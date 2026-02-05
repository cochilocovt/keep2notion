# HTTPS Configuration Guide

This document describes how to configure HTTPS/TLS for all external-facing services in the Keep-Notion-Sync application.

## Overview

The application uses AWS Certificate Manager (ACM) for SSL/TLS certificates and the AWS Load Balancer Controller to automatically configure HTTPS on the Application Load Balancer.

## Architecture

```
Internet (HTTPS) → ALB (TLS Termination) → Kubernetes Services (HTTP)
```

- **External Traffic**: HTTPS only (port 443)
- **ALB to Services**: HTTP (internal cluster network)
- **Service-to-Service**: HTTP (internal cluster network, secured by network policies)

## Prerequisites

1. **Domain Names**: You need domain names for your services
   - `api.keep-notion-sync.example.com` - API Gateway
   - `admin.keep-notion-sync.example.com` - Admin Interface

2. **AWS Certificate Manager**: SSL/TLS certificate for your domains

3. **Route 53 or External DNS**: DNS configuration

## Step 1: Request SSL/TLS Certificate

### Option A: Using AWS Certificate Manager (Recommended)

1. **Request a certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name "*.keep-notion-sync.example.com" \
     --subject-alternative-names "keep-notion-sync.example.com" \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Get certificate ARN**:
   ```bash
   aws acm list-certificates --region us-east-1
   ```

3. **Validate certificate**:
   - Add the CNAME records provided by ACM to your DNS
   - Wait for validation (usually 5-30 minutes)

4. **Verify certificate status**:
   ```bash
   aws acm describe-certificate \
     --certificate-arn arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID \
     --region us-east-1
   ```

### Option B: Using Terraform

Add to `deployment/terraform/acm.tf`:

```hcl
# ACM Certificate
resource "aws_acm_certificate" "main" {
  domain_name               = "*.keep-notion-sync.example.com"
  subject_alternative_names = ["keep-notion-sync.example.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

# DNS Validation (if using Route 53)
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

output "acm_certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = aws_acm_certificate.main.arn
}
```

## Step 2: Update Ingress Configuration

Update `deployment/kubernetes/ingress.yaml` with your certificate ARN:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: keep-notion-sync-ingress
  namespace: keep-notion-sync
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    
    # HTTPS Configuration
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID
    
    # Security Headers
    alb.ingress.kubernetes.io/actions.ssl-redirect: |
      {
        "Type": "redirect",
        "RedirectConfig": {
          "Protocol": "HTTPS",
          "Port": "443",
          "StatusCode": "HTTP_301"
        }
      }
spec:
  rules:
  - host: api.keep-notion-sync.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway-service
            port:
              number: 8000
  - host: admin.keep-notion-sync.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: admin-interface-service
            port:
              number: 8080
```

## Step 3: Configure Security Headers

Add security headers to your services:

### API Gateway (FastAPI)

Update `services/api_gateway/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# HTTPS Redirect (only in production)
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted Host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.keep-notion-sync.example.com", "localhost"]
)

# Security Headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

### Admin Interface (Django)

Update `services/admin_interface/sync_admin/settings.py`:

```python
# HTTPS/SSL Settings
if os.getenv("ENVIRONMENT") == "production":
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Allowed Hosts
ALLOWED_HOSTS = [
    'admin.keep-notion-sync.example.com',
    'localhost',
    '127.0.0.1'
]

# CORS Settings (if needed)
CORS_ALLOWED_ORIGINS = [
    "https://api.keep-notion-sync.example.com",
    "https://admin.keep-notion-sync.example.com",
]
```

## Step 4: Configure DNS

### Option A: Using Route 53

```bash
# Get ALB DNS name
ALB_DNS=$(kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create CNAME records
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.keep-notion-sync.example.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "admin.keep-notion-sync.example.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
        }
      }
    ]
  }'
```

### Option B: Manual DNS Configuration

1. Get the ALB DNS name:
   ```bash
   kubectl get ingress keep-notion-sync-ingress -n keep-notion-sync
   ```

2. In your DNS provider, create CNAME records:
   - `api.keep-notion-sync.example.com` → ALB DNS name
   - `admin.keep-notion-sync.example.com` → ALB DNS name

## Step 5: Verify HTTPS Configuration

### Test HTTPS Endpoints

```bash
# Test API Gateway
curl -I https://api.keep-notion-sync.example.com/api/v1/health

# Test Admin Interface
curl -I https://admin.keep-notion-sync.example.com/admin/

# Verify HTTP redirects to HTTPS
curl -I http://api.keep-notion-sync.example.com/api/v1/health
```

### Check SSL Certificate

```bash
# Using OpenSSL
openssl s_client -connect api.keep-notion-sync.example.com:443 -servername api.keep-notion-sync.example.com

# Using curl
curl -vI https://api.keep-notion-sync.example.com/api/v1/health 2>&1 | grep -A 10 "SSL connection"
```

### Test Security Headers

```bash
curl -I https://api.keep-notion-sync.example.com/api/v1/health | grep -E "(Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options)"
```

### SSL Labs Test

Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.keep-notion-sync.example.com

## Step 6: Internal Service Communication

Internal services communicate over HTTP within the cluster. To add TLS for internal communication (optional):

### Create Internal CA Certificate

```bash
# Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/CN=Keep-Notion-Sync Internal CA"

# Create Kubernetes secret
kubectl create secret generic internal-ca \
  --from-file=ca.crt=ca.crt \
  --from-file=ca.key=ca.key \
  -n keep-notion-sync
```

### Generate Service Certificates

```bash
# For each service
for SERVICE in api-gateway sync-service keep-extractor notion-writer; do
  # Generate key
  openssl genrsa -out ${SERVICE}.key 2048
  
  # Generate CSR
  openssl req -new -key ${SERVICE}.key -out ${SERVICE}.csr \
    -subj "/CN=${SERVICE}.keep-notion-sync.svc.cluster.local"
  
  # Sign with CA
  openssl x509 -req -in ${SERVICE}.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out ${SERVICE}.crt -days 365
  
  # Create secret
  kubectl create secret tls ${SERVICE}-tls \
    --cert=${SERVICE}.crt \
    --key=${SERVICE}.key \
    -n keep-notion-sync
done
```

## Troubleshooting

### Certificate Not Working

1. **Check certificate status**:
   ```bash
   aws acm describe-certificate --certificate-arn YOUR_CERT_ARN
   ```

2. **Verify DNS validation**:
   ```bash
   dig CNAME_RECORD_NAME
   ```

3. **Check ingress annotations**:
   ```bash
   kubectl describe ingress keep-notion-sync-ingress -n keep-notion-sync
   ```

### HTTP Not Redirecting to HTTPS

1. **Check ALB listener rules**:
   ```bash
   aws elbv2 describe-listeners --load-balancer-arn YOUR_ALB_ARN
   ```

2. **Verify ingress annotations**:
   - Ensure `alb.ingress.kubernetes.io/ssl-redirect: '443'` is set

### Certificate Mismatch

1. **Verify domain names** in certificate match your ingress hosts
2. **Check Subject Alternative Names (SANs)** include all required domains

### Mixed Content Warnings

1. **Ensure all resources** (CSS, JS, images) are loaded over HTTPS
2. **Update hardcoded URLs** to use relative paths or HTTPS

## Security Best Practices

1. **Use Strong Cipher Suites**: ACM automatically uses secure ciphers
2. **Enable HSTS**: Set `Strict-Transport-Security` header
3. **Regular Certificate Rotation**: ACM handles automatic renewal
4. **Monitor Certificate Expiry**: Set up CloudWatch alarms
5. **Disable TLS 1.0/1.1**: ACM uses TLS 1.2+ by default
6. **Use Certificate Pinning**: For mobile apps (if applicable)
7. **Implement CSP**: Content Security Policy headers

## Monitoring

### CloudWatch Metrics

Monitor ALB metrics:
- `TargetResponseTime`
- `HTTPCode_Target_4XX_Count`
- `HTTPCode_Target_5XX_Count`
- `RequestCount`

### Certificate Expiry Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name keep-notion-sync-cert-expiry \
  --alarm-description "Alert when certificate is expiring" \
  --metric-name DaysToExpiry \
  --namespace AWS/CertificateManager \
  --statistic Minimum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=CertificateArn,Value=YOUR_CERT_ARN
```

## Additional Resources

- [AWS Certificate Manager Documentation](https://docs.aws.amazon.com/acm/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
