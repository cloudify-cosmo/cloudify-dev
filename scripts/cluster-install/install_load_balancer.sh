#! /usr/bin/env bash
# Abort on any failures
set -eux

sudo yum install -y haproxy

cat $7/certs/load_balancer_cert.pem $7/certs/load_balancer_key.pem > $7/certs/cert.pem
sudo mv $7/certs/cert.pem /etc/haproxy
sudo chown haproxy. /etc/haproxy/cert.pem
sudo chmod 400 /etc/haproxy/cert.pem

sudo cp $7/certs/ca.crt /etc/haproxy
sudo chown haproxy. /etc/haproxy/ca.crt

sudo restorecon /etc/haproxy/*

echo "global
    maxconn 100
    tune.ssl.default-dh-param 2048
defaults
    log global
    retries 2
    timeout client 30m
    timeout connect 4s
    timeout server 30m
    timeout check 5s
listen manager
    bind *:80
    bind *:443 ssl crt /etc/haproxy/cert.pem
    redirect scheme https if !{ ssl_fc }
    mode http
    option forwardfor
    stick-table type ip size 1m expire 1h
    stick on src
    option httpchk GET /api/v3.1/status
    http-check expect status 401
    default-server inter 3s fall 3 rise 2 on-marked-down shutdown-sessions
    server manager_$1 $2 maxconn 100 ssl check check-ssl port 443 ca-file /etc/haproxy/ca.crt
    server manager_$3 $4 maxconn 100 ssl check check-ssl port 443 ca-file /etc/haproxy/ca.crt
    server manager_$5 $6 maxconn 100 ssl check check-ssl port 443 ca-file /etc/haproxy/ca.crt" | sudo tee /etc/haproxy/haproxy.cfg
sudo systemctl enable haproxy
sudo systemctl restart haproxy
