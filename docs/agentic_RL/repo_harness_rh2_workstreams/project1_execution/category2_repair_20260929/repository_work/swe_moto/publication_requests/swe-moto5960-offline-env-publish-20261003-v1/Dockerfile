ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY wheels/ /opt/rh2/build-wheels/
ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels
