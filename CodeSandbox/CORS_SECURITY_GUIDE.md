# CORS Security Configuration Guide

## Overview

Cross-Origin Resource Sharing (CORS) is a security mechanism that allows or restricts web applications from making requests to different domains. This guide covers secure CORS configuration for the CodeSandbox application.

## ⚠️ Critical Security Rules

### 1. **NEVER use `*` with credentials in production**
```bash
# ❌ DANGEROUS - Major security vulnerability
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=production
```

This combination allows **ANY domain** to make authenticated requests to your API, potentially exposing user data to malicious websites.

### 2. **Always include protocols**
```bash
# ❌ Wrong - Missing protocol
CORS_ORIGINS=mydomain.com,localhost:3000

# ✅ Correct - Includes protocol
CORS_ORIGINS=https://mydomain.com,http://localhost:3000
```

### 3. **No wildcard patterns allowed**
```bash
# ❌ Wrong - Wildcard patterns not supported by CORS spec
CORS_ORIGINS=*.mydomain.com

# ✅ Correct - Explicit subdomains
CORS_ORIGINS=https://app.mydomain.com,https://admin.mydomain.com
```

## Environment Configuration Examples

### Development Environment
```bash
# Development - Allows all origins (⚠️ development only!)
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=development
```

### Local Development with Specific Origins
```bash
# Local development - Specific local origins
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=development
```

### Production - Single Domain
```bash
# Production - Single domain setup
CORS_ORIGINS=https://codesandbox.mydomain.com
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=production
```

### Production - Multiple Subdomains
```bash
# Production - Multiple subdomains
CORS_ORIGINS=https://app.mydomain.com,https://admin.mydomain.com,https://api.mydomain.com
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=production
```

### Production - CDN + Main Domain
```bash
# Production - CDN and main domain
CORS_ORIGINS=https://cdn.mydomain.com,https://mydomain.com
CORS_ALLOW_CREDENTIALS=true
ENVIRONMENT=production
```

## Environment File Format Rules

### ✅ Correct Format
```bash
# NO spaces after commas
CORS_ORIGINS=https://domain1.com,https://domain2.com,https://domain3.com
```

### ❌ Incorrect Format
```bash
# Spaces after commas will break parsing
CORS_ORIGINS=https://domain1.com, https://domain2.com, https://domain3.com
```

## Security Validation

The CodeSandbox application automatically validates your CORS configuration and will warn you about security issues:

```
WARNING: Using CORS_ORIGINS=* with CORS_ALLOW_CREDENTIALS=true in production 
is a MAJOR security risk. This allows ANY domain to make authenticated requests 
to your API. Please specify explicit origins for production.
```

## Testing Your CORS Configuration

### 1. Browser Developer Tools
- Open Network tab
- Check request headers for `Origin`
- Check response headers for `Access-Control-Allow-Origin`

### 2. curl Testing
```bash
# Test with specific origin
curl -H "Origin: https://yourdomain.com" \
     -H "Authorization: token your-token" \
     -v http://localhost:8888/api/status

# Should return:
# Access-Control-Allow-Origin: https://yourdomain.com
```

### 3. JavaScript Testing
```javascript
// Test CORS request from browser console
fetch('/api/status', {
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => console.log('CORS working:', response.status))
.catch(error => console.error('CORS error:', error));
```

## Common CORS Errors and Solutions

### Error: "Access to fetch has been blocked by CORS policy"
**Cause:** Origin not in allowed list or missing protocol

**Solution:**
```bash
# Add your domain with protocol to CORS_ORIGINS
CORS_ORIGINS=https://your-frontend-domain.com
```

### Error: "CORS policy: The request client is not a secure context"
**Cause:** Using HTTP in production with credentials

**Solution:**
```bash
# Use HTTPS in production
CORS_ORIGINS=https://yourdomain.com  # Not http://
```

### Error: "Cannot use wildcard in Access-Control-Allow-Origin when credentials flag is true"
**Cause:** Using `*` with credentials

**Solution:**
```bash
# Specify explicit origins
CORS_ORIGINS=https://yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

## Deployment Checklist

- [ ] ✅ `CORS_ORIGINS` specifies explicit domains (no `*` in production)
- [ ] ✅ All origins include protocol (`https://` or `http://`)
- [ ] ✅ No spaces after commas in origin list
- [ ] ✅ All origins are domains you control
- [ ] ✅ Test from actual frontend domain
- [ ] ✅ Verify no CORS errors in browser console
- [ ] ✅ Check that API responses include correct CORS headers

## Advanced Configuration

### Reverse Proxy Alternative
If you're using Nginx or similar, you can avoid CORS entirely by proxying:

```nginx
location /api/ {
    proxy_pass http://localhost:8888/;
    proxy_set_header Host $host;
    proxy_set_header Origin $http_origin;
}
```

### Environment-Specific Origins
```javascript
// In your frontend build process
const API_BASE = process.env.NODE_ENV === 'production' 
  ? 'https://api.mydomain.com'
  : 'http://localhost:8888';
```

## Resources

- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [CORS Security Best Practices](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#Security)
- [OWASP CORS Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Origin_Resource_Sharing_Cheat_Sheet.html)

## Questions or Issues?

If you encounter CORS issues:
1. Check the browser console for specific error messages
2. Verify your environment file configuration
3. Test with curl to isolate frontend vs backend issues
4. Review this guide for common patterns 