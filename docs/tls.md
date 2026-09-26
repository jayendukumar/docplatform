# TLS deployment reference

The application serves HTTP on its private container port. For any non-local deployment, terminate TLS at a reverse proxy and forward only to the loopback/private application endpoint. Set `DOCPLATFORM_SECURE_COOKIES=true` (or `secure_cookies = true` in the mounted TOML file) so login cookies are sent only over HTTPS.

## Caddy

```caddyfile
docs.example.test {
    reverse_proxy 127.0.0.1:8001
}
```

Caddy obtains and renews certificates for a real public hostname when its normal certificate prerequisites are met. For a private test certificate, configure Caddy's documented internal issuer and trust that CA explicitly; do not disable certificate verification in clients.

## Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name docs.example.test;
    ssl_certificate     /etc/letsencrypt/live/docs.example.test/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/docs.example.test/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

The proxy must protect the certificate key, restrict the upstream to the application host, and use an explicit certificate renewal process. The reference does not claim certificate issuance, domain ownership, HSTS policy, or a production security review.

## Local verification

The default Compose service intentionally binds to `127.0.0.1:8001` for local development. Test the application directly with `http://localhost:8001`; do not enable `secure_cookies` unless the browser-facing URL is HTTPS, or the browser will correctly withhold the session cookie over HTTP.
