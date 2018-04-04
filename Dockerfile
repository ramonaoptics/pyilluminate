FROM continuumio/miniconda3

RUN conda install -y conda-build flake8

RUN curl "https://raw.githubusercontent.com/hmaarrfk/Dropbox-Uploader/master/dropbox_uploader.sh" -o /usr/bin/dropbox_uploader.sh
RUN chmod +x /usr/bin/dropbox_uploader.sh

# ENV BITBUCKET_BUILD_DIR="/opt/atlassian/pipelines/agent/build"
# COPY . /$BITBUCKET_BUILD_DIR
# WORKDIR /$BITBUCKET_BUILD_DIR
# ENV DBU_OAUTH_ACCESS_TOKEN=
