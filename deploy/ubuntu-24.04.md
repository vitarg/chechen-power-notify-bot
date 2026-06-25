# Деплой на Ubuntu 24.04

## Пакеты

```bash
sudo apt update
sudo apt install -y python3.12-venv python3-pip postgresql postgresql-client git
```

## Пользователь и база

```bash
sudo useradd --system --create-home --home-dir /opt/chechen-power-notify chechen-power
sudo -u postgres createuser chechen_power
sudo -u postgres createdb chechen_power -O chechen_power
sudo -u postgres psql -c "ALTER USER chechen_power WITH PASSWORD 'change-me';"
```

## Приложение

```bash
sudo -u chechen-power git clone <repo-url> /opt/chechen-power-notify
cd /opt/chechen-power-notify
sudo -u chechen-power python3.12 -m venv .venv
sudo -u chechen-power .venv/bin/pip install -e .
sudo -u chechen-power cp .env.example .env
sudo -u chechen-power nano .env
sudo -u chechen-power .venv/bin/alembic upgrade head
```

## systemd

```bash
sudo cp deploy/chechen-power-notify.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chechen-power-notify
sudo journalctl -u chechen-power-notify -f
```

## Бэкапы

```bash
sudo install -m 0755 scripts/backup_postgres.sh /usr/local/bin/chechen-power-backup
sudo crontab -e
```

Cron:

```text
15 3 * * * /usr/local/bin/chechen-power-backup
```

