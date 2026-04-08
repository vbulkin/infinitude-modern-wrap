# Build from fresh Alpine — the nebulous/infinitude base deletes apk-tools,
# making it impossible to install additional packages.
FROM alpine:latest

# Install all Perl dependencies (matching nebulous/infinitude) plus SSL and tools
RUN apk add --no-cache \
    perl perl-mojolicious perl-chi perl-datetime \
    perl-path-tiny perl-json perl-xml-simple perl-moo perl-io-tty \
    perl-app-cpanminus make \
    perl-io-socket-ssl perl-net-ssleay \
    jq curl && \
    cpanm -n Data::ParseBinary Digest::CRC Hash::AsObject IO::Termios && \
    apk del make perl-app-cpanminus

# Copy infinitude application from upstream image
COPY --from=nebulous/infinitude:latest /infinitude /infinitude
WORKDIR /infinitude

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

EXPOSE 3000

# Preserve original UI as native.html, serve ours as default
RUN cp /infinitude/public/dist/index.html /infinitude/public/dist/native.html

COPY infinitude-ui.html /infinitude/public/dist/index.html

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
