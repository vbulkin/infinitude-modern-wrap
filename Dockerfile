FROM nebulous/infinitude:latest

# Preserve original UI as native.html, serve ours as default
RUN cp /infinitude/public/dist/index.html /infinitude/public/dist/native.html

COPY infinitude-ui.html /infinitude/public/dist/index.html

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
