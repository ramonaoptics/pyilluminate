# pyIlluminate

Python interface for controlling the [Illuminate](https://github.com/zfphil/illuminate) boards.

All units to this interface are in SI units.

# Deployment

Using pipelines will build the image for linux-64 and win-64 and upload them
to Mark Harfouche's dropbox automatically:

Make sure you install dropbox_uploader from hmaarrfk that allows you to set environment variables
You can follow instructions https://www.dropbox.com/developers/apps

Then set the `DBU_OAUTH_ACCESS_TOKEN` to the appropriate value
