#!/bin/sh
# Run Hermes as the nutrigent user with the NutriGent profile (/opt/nutrigent/.hermes).
cd /opt/nutrigent || exit 1
exec sudo -u nutrigent -H env HOME=/opt/nutrigent HERMES_HOME=/opt/nutrigent/.hermes /opt/nutrigent/.local/bin/hermes "$@"
