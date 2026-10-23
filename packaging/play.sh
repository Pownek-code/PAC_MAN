#!/bin/sh
# Start the game with the configuration file shipped next to it.
cd "$(dirname "$0")" && exec ./pac-man config.json
