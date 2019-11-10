#compile deps stage
FROM python:3.7-alpine as build
COPY /alfred/requirements.txt /app/requirements.txt
RUN apk update && \
    apk add gcc musl-dev postgresql-dev libffi-dev python3-dev
RUN pip install -r /app/requirements.txt
#default stage
FROM python:3.7-alpine
RUN apk update && \
    apk add libpq
COPY --from=build /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/
COPY /alfred /app
WORKDIR /app
CMD ["python", "alfred.py"]