FROM nebulous/infinitude:latest

# Install jq for reliable JSON parsing of HA add-on options
# Install perl SSL modules so Mojo::UserAgent can forward HTTPS to Carrier
RUN apk add --no-cache jq perl-io-socket-ssl perl-net-ssleay 2>/dev/null || true

# Preserve original UI as native.html, serve ours as default
RUN cp /infinitude/public/dist/index.html /infinitude/public/dist/native.html

COPY infinitude-ui.html /infinitude/public/dist/index.html

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
