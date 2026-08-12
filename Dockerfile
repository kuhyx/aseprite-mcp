# Slim, apt-based image: far faster to build than bootstrapping Homebrew
# just to get Python + uv.
FROM python:3.13-slim

RUN pip install --no-cache-dir uv

# --- Optional Steam/Aseprite support ---
# steamcmd lives in Debian's non-free component and needs the i386 arch
# (it's a 32-bit bootstrapper) plus non-interactive EULA acceptance.
RUN dpkg --add-architecture i386 \
	&& sed -i 's/^Components: .*/Components: main contrib non-free non-free-firmware/' /etc/apt/sources.list.d/debian.sources \
	&& echo steam steam/question select "I AGREE" | debconf-set-selections \
	&& echo steam steam/license note '' | debconf-set-selections \
	&& apt-get update \
	&& DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
	   steamcmd lib32gcc-s1 ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Steam/Aseprite environment knobs (no secrets baked!)
ENV STEAM_APPID=431730 \
	STEAM_INSTALL_DIR=/opt/steamapps

# Set the working directory
WORKDIR /app

# Copy the project files (including helper scripts)
COPY . .

# Install Python dependencies using uv
RUN uv sync

# Ensure helper scripts are executable
RUN chmod +x scripts/*.sh || true

# Use a wrapper entrypoint that can install Aseprite via Steam at runtime if requested
ENTRYPOINT ["/bin/bash", "/app/scripts/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD []
