# coffeebot
Coffee via Vobot
```
docker pull vobot/mini-dock-app-dev:latest
docker run \
    --rm -it \
    -v $(pwd):/work/disk/apps/coffeebot \
    --network=bridge \
    -e DISPLAY="10.0.0.10:0" \
    vobot/mini-dock-app-dev:latest --publish 8080:80

```