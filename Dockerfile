FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY adapt_docs.py .
COPY mkdocs.yml .
COPY research/ research/
COPY docs/ docs/

# Generate docs from research sources, then build site
RUN python adapt_docs.py && mkdocs build

FROM nginx:alpine

COPY --from=builder /build/site/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY .htpasswd /etc/nginx/.htpasswd

EXPOSE 80
