# Distributed Word Counter

A distributed word-counting system built with [RPyC](https://rpyc.readthedocs.io/) and Flask. A client splits an input document into chunks and dispatches each chunk to a slave/worker node for processing over RPC; results are aggregated and returned via a simple web UI.

## Architecture

- **`word_counter_server.py`** — RPyC service (`WordCountService`) that exposes `count_words`, tokenizing a text chunk and returning word frequencies. Run one instance per worker node, each bound to one of three fixed ports (`18861`, `18862`, `18863`).
- **`client.py`** — Text preprocessing (tokenizing, lowercasing, stopword removal via NLTK), chunk splitting, and RPC client logic (`connect_to_slave`, `process_chunk`) with retry handling.
- **`app.py`** — Flask web app. Accepts a `.txt`/`.pdf` upload or raw text, preprocesses it, splits it across the configured slave servers, aggregates the returned word counts, and returns the top results as JSON.

```
Browser → Flask app (app.py) → client.py → RPyC slaves (word_counter_server.py × 3)
```

## Requirements

- Python 3
- `rpyc`, `nltk`, `flask`, `python-dotenv`, `PyPDF2`, `werkzeug`
- NLTK corpora: `stopwords`, `punkt_tab` (downloaded automatically on app start)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The Flask app reads slave connection details from environment variables (e.g. via a `.env` file):

```
SLAVE1_IP=...
SLAVE1_PORT=18861
SLAVE2_IP=...
SLAVE2_PORT=18862
SLAVE3_IP=...
SLAVE3_PORT=18863
```

## Running Locally

1. Start each slave server on its designated port:
   ```bash
   python3 word_counter_server.py 18861
   python3 word_counter_server.py 18862
   python3 word_counter_server.py 18863
   ```
2. Start the Flask app:
   ```bash
   python3 app.py
   ```
3. Open `http://localhost:5000` and submit text or a file to process.

## Deploying to AWS

This project is designed to run across multiple EC2 instances: one client/app node and three slave nodes.

### 1. Launch EC2 instances
- 1 client instance + 3 slave instances
- Recommended: `t2.micro`/`t3.micro` (free tier), Ubuntu Server or Amazon Linux 2
- Use the same region for all instances to minimize latency

### 2. Configure security groups
| Type | Protocol | Port range | Source |
|---|---|---|---|
| SSH | TCP | 22 | Your IP only |
| Custom TCP | TCP | 18861–18863 | Private IPs of the other instances in the VPC |
| HTTP | TCP | 80 | As needed for the app |
| Custom TCP | TCP | 5000 | As needed for the Flask app |

Restrict inter-node traffic to private IPs within the same VPC rather than opening it to the internet. Note that AWS EC2 Instance Connect uses an AWS-managed IP range, so locking SSH to a single personal IP will block it — allow for that if you rely on Instance Connect.

### 3. Set up each slave node
```bash
ssh -i your-key.pem ubuntu@<slave-public-dns>
sudo apt update
sudo apt install python3-venv -y
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```
Copy `word_count_server.py` to the instance, then start it manually or via the systemd service below.

### 4. Set up the client/app node
```bash
ssh -i your-key.pem ubuntu@<client-public-dns>
mkdir -p ~/word_counter
```
Copy `app.py`, `client.py`, and related files, install dependencies, and update the `.env` file with the slaves' private IPs and ports.

### 5. Run as systemd services

**Slave service** — `/etc/systemd/system/word-counter-slave.service`:
```ini
[Unit]
Description=Word Counter Slave Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/cep/distributed-word-counter
ExecStart=/home/ubuntu/cep/distributed-word-counter/myenv/bin/python3 /home/ubuntu/cep/distributed-word-counter/word_count_server.py 18862
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable word-counter-slave
sudo systemctl start word-counter-slave
sudo systemctl status word-counter-slave
```

### 6. Serve the app with Gunicorn + Nginx

For production, run the Flask app behind Gunicorn (a WSGI server) with Nginx as a reverse proxy in front of it, rather than using Flask's development server.

- **Gunicorn** runs the Flask app with multiple worker processes for better throughput and stability.
- **Nginx** handles incoming HTTP/HTTPS traffic, forwards it to Gunicorn on a local port, serves static assets, and manages things like SSL termination and load balancing.

```bash
pip install gunicorn
```

Create a `wsgi.py` entry point, then a systemd service at `/etc/systemd/system/word-counter.service` to run Gunicorn bound to your app, and enable/start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable word-counter
sudo systemctl start word-counter
sudo systemctl status word-counter
```

Configure Nginx at `/etc/nginx/sites-available/word-counter` to proxy to `localhost:5000` (or your Gunicorn bind address), preserving headers for logging/routing. Enable the site and test:

```bash
sudo ln -s /etc/nginx/sites-available/word-counter /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

**Connection refused between nodes**
- Confirm the security group allows traffic on the RPC ports between instances
- Check the slave service status: `sudo systemctl status word-counter-slave`
- Restart if needed: `sudo systemctl restart word-counter-slave`

**Timeout issues**
- Verify network connectivity between instances (private IPs, same VPC/subnet)
- Increase `sync_request_timeout` in the RPyC client config if chunks are large

**`OSError: [Errno 98] Address already in use`**
```bash
sudo lsof -i :<port>
sudo kill -9 <pid>
```

**Permission issues**
```bash
chmod 644 word_count_server.py client.py
chmod +x setup_slave.sh
```

**SSH disconnects after inactivity**
Add to `~/.ssh/config`:
```
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

## Security Notes

- Prefer private IPs for inter-node (RPC) traffic since all instances share a VPC — private IPv4 addresses aren't reachable from the public internet.
- Scope the RPC ports (18861–18863) to only the private IPs of your other instances, not `0.0.0.0/0`.
- Scope SSH (port 22) to your own IP; remember this can interfere with EC2 Instance Connect, which uses AWS-managed IPs.
- Update Flask configuration for production (disable debug mode) before deploying behind Gunicorn/Nginx.
