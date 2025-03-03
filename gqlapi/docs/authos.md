# Authos GQL Service Docs

## Endpoints

### Get Session Token

- GraphQL Query

```gql
query getSessionToken($secretKey: String!) {
  getEcommerceSessionToken(refSecretKey: $secretKey) {
    ... on EcommerceSession {
      ecommerceUserId
      sessionData
      expiration
      sessionToken
      status
      msg
    }
    ... on EcommerceSessionError {
      msg
      code
    }
  }
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk"
}
```

### Get Session Token (with Refresh)

- GraphQL Query

```gql
query getSessionTokenRefresh($secretKey: String!) {
  getEcommerceSessionToken(refSecretKey: $secretKey, refresh: true) {
    ... on EcommerceSession {
      ecommerceUserId
      sessionData
      expiration
      sessionToken
      status
      msg
    }
    ... on EcommerceSessionError {
      msg
      code
    }
  }
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk"
}
```

- Headers

```json
{
  "Authorization": "ecbasic-migomekjgpk eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiMC4wLjAuMDo4MDA0IiwiY29ubmVjdGlvbiI6ImtlZXAtYWxpdmUiLCJjb250ZW50LWxlbmd0aCI6IjQwMyIsImFjY2VwdCI6ImFwcGxpY2F0aW9uL2pzb24sIG11bHRpcGFydC9taXhlZCIsInVzZXItYWdlbnQiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTE5LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJjb250ZW50LXR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIiwib3JpZ2luIjoiaHR0cDovLzAuMC4wLjA6ODAwNCIsInJlZmVyZXIiOiJodHRwOi8vMC4wLjAuMDo4MDA0L2dyYXBocWwiLCJhY2NlcHQtZW5jb2RpbmciOiJnemlwLCBkZWZsYXRlIiwiYWNjZXB0LWxhbmd1YWdlIjoiZXMtNDE5LGVzO3E9MC45IiwiaXB2NC1hZGRyZXNzIjoiMTI3LjAuMC4xIiwicmVmX3NlY3JldF9rZXkiOiJtaWdvbWVramdwayIsImV4cCI6MTcwMDIwMDM0M30.irxIt88bl051tI6KNI1bYgl2CdaCx43uED0gtDGHqTk"
}
```

### Is User Logged In

- GraphQL Query

```gql
query isUserLoggedIn($secretKey: String!) {
  isEcommerceUserLoggedIn(refSecretKey: $secretKey) {
    ... on EcommerceUserMsg {
      status
      msg
    }
    ... on EcommerceUserError {
      msg
      code
    }
  }
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk"
}
```

- Headers

```json
{
  "Authorization": "ecbasic-migomekjgpk eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiMC4wLjAuMDo4MDA0IiwiY29ubmVjdGlvbiI6ImtlZXAtYWxpdmUiLCJjb250ZW50LWxlbmd0aCI6IjQwMyIsImFjY2VwdCI6ImFwcGxpY2F0aW9uL2pzb24sIG11bHRpcGFydC9taXhlZCIsInVzZXItYWdlbnQiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTE5LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJjb250ZW50LXR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIiwib3JpZ2luIjoiaHR0cDovLzAuMC4wLjA6ODAwNCIsInJlZmVyZXIiOiJodHRwOi8vMC4wLjAuMDo4MDA0L2dyYXBocWwiLCJhY2NlcHQtZW5jb2RpbmciOiJnemlwLCBkZWZsYXRlIiwiYWNjZXB0LWxhbmd1YWdlIjoiZXMtNDE5LGVzO3E9MC45IiwiaXB2NC1hZGRyZXNzIjoiMTI3LjAuMC4xIiwicmVmX3NlY3JldF9rZXkiOiJtaWdvbWVramdwayIsImV4cCI6MTcwMDIwMDM0M30.irxIt88bl051tI6KNI1bYgl2CdaCx43uED0gtDGHqTk"
}
```

### Sign Up User

- GraphQL Query

```gql
mutation signupUser($email: String!, $pwd: String!, $fName: String!, $lName: String!, $phoneNumber: String!, $secretKey: String!, $url: String!) {
  signupEcommerceUser(
    email: $email
    firstName: $fName
    lastName: $lName
    password: $pwd
    phoneNumber: $phoneNumber
    refSecretKey: $secretKey
    refUrl: $url
  ) {
    ... on EcommerceUser {
      id
      email
      firstName
      lastName
      phoneNumber
      disabled
      createdAt
      session {
        sessionToken
        status
        expiration
        msg
      }
    }
    ... on EcommerceUserError {
      msg
      code
    }
  }
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk",
  "email": "jjjjjjj@hotmail.com",
  "fName": "jorge",
  "lName": "vizcayno",
  "pwd": "babababa",
  "phoneNumber": "7757780901",
  "url": "https://alima.la"
}
```

- Headers 

```json
{
  "Authorization": "ecbasic-migomekjgpk eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiMC4wLjAuMDo4MDA0IiwiY29ubmVjdGlvbiI6ImtlZXAtYWxpdmUiLCJjb250ZW50LWxlbmd0aCI6IjQwMyIsImFjY2VwdCI6ImFwcGxpY2F0aW9uL2pzb24sIG11bHRpcGFydC9taXhlZCIsInVzZXItYWdlbnQiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTE5LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJjb250ZW50LXR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIiwib3JpZ2luIjoiaHR0cDovLzAuMC4wLjA6ODAwNCIsInJlZmVyZXIiOiJodHRwOi8vMC4wLjAuMDo4MDA0L2dyYXBocWwiLCJhY2NlcHQtZW5jb2RpbmciOiJnemlwLCBkZWZsYXRlIiwiYWNjZXB0LWxhbmd1YWdlIjoiZXMtNDE5LGVzO3E9MC45IiwiaXB2NC1hZGRyZXNzIjoiMTI3LjAuMC4xIiwicmVmX3NlY3JldF9rZXkiOiJtaWdvbWVramdwayIsImV4cCI6MTcwMDIwMDM0M30.irxIt88bl051tI6KNI1bYgl2CdaCx43uED0gtDGHqTk"
}
```

### Login User

- GraphQL Query

```gql
mutation loginUser($secretKey: String!, $email: String!, $pwd: String!) {
  loginEcommerceUser(email: $email, password: $pwd, refSecretKey: $secretKey) {
    ... on EcommerceUserError {
      msg
      code
    }
    ... on EcommerceUser {
      id
      email
      firstName
      lastName
      phoneNumber
      session {
        sessionToken
        expiration
        status
        msg
      }
    }
  }
}
```

- Headers

```json
{
  "Authorization": "ecbasic-migomekjgpk eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiMC4wLjAuMDo4MDA0IiwiY29ubmVjdGlvbiI6ImtlZXAtYWxpdmUiLCJjb250ZW50LWxlbmd0aCI6IjQwMyIsImFjY2VwdCI6ImFwcGxpY2F0aW9uL2pzb24sIG11bHRpcGFydC9taXhlZCIsInVzZXItYWdlbnQiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTE5LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJjb250ZW50LXR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIiwib3JpZ2luIjoiaHR0cDovLzAuMC4wLjA6ODAwNCIsInJlZmVyZXIiOiJodHRwOi8vMC4wLjAuMDo4MDA0L2dyYXBocWwiLCJhY2NlcHQtZW5jb2RpbmciOiJnemlwLCBkZWZsYXRlIiwiYWNjZXB0LWxhbmd1YWdlIjoiZXMtNDE5LGVzO3E9MC45IiwiaXB2NC1hZGRyZXNzIjoiMTI3LjAuMC4xIiwicmVmX3NlY3JldF9rZXkiOiJtaWdvbWVramdwayIsImV4cCI6MTcwMDIwMDM0M30.irxIt88bl051tI6KNI1bYgl2CdaCx43uED0gtDGHqTk"
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk",
  "email": "hola@hotmail.com",
  "pwd": "babababa"
}
```

### Logout User 

- GraphQL Query

```gql
mutation logoutUser($secretKey: String!) {
  logoutEcommerceUser(refSecretKey: $secretKey) {
    ... on EcommerceUserMsg {
      msg
      status
    }
    ... on EcommerceUserError {
      code
      msg
    }
  }
}
```

- Headers 

```json
{
  "Authorization": "ecbasic-migomekjgpk eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJob3N0IjoiMC4wLjAuMDo4MDA0IiwiY29ubmVjdGlvbiI6ImtlZXAtYWxpdmUiLCJjb250ZW50LWxlbmd0aCI6IjQwMyIsImFjY2VwdCI6ImFwcGxpY2F0aW9uL2pzb24sIG11bHRpcGFydC9taXhlZCIsInVzZXItYWdlbnQiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTE5LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJjb250ZW50LXR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIiwib3JpZ2luIjoiaHR0cDovLzAuMC4wLjA6ODAwNCIsInJlZmVyZXIiOiJodHRwOi8vMC4wLjAuMDo4MDA0L2dyYXBocWwiLCJhY2NlcHQtZW5jb2RpbmciOiJnemlwLCBkZWZsYXRlIiwiYWNjZXB0LWxhbmd1YWdlIjoiZXMtNDE5LGVzO3E9MC45IiwiaXB2NC1hZGRyZXNzIjoiMTI3LjAuMC4xIiwicmVmX3NlY3JldF9rZXkiOiJtaWdvbWVramdwayIsImV4cCI6MTcwMDIwMDM0M30.irxIt88bl051tI6KNI1bYgl2CdaCx43uED0gtDGHqTk"
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk"
}
```

### Send Password Restore Code

- GraphQL Query

```gql
mutation sendRestoreCode($secretKey: String!, $email: String!, $url: String!) {
  postEcommerceSendRestoreCode(email: $email, refSecretKey: $secretKey, url: $url) {
    ... on EcommercePassword {
      restoreToken
      status
      msg
      ecommerceUserId
      expiration
    }
    ... on EcommercePasswordError {
      msg
      code
    }
  }
}
```

- Variables

```json
{
  "secretKey": "migomekjgpk",
  "email": "javg44@hotmail.com",
  "url": "https://app.alima.la"
}
```

### Reset Password with restore code

- GraphQL Query

```gql
mutation resetPassword($secretKey: String!, $newPwd: String!, $resToken: String!) {
  postEcommerceResetPassword(
    password: $newPwd
    refSecretKey: $secretKey
    restoreToken: $resToken
  ) {
    ... on EcommercePasswordResetMsg {
      msg
      status
    }
    ... on EcommercePasswordError {
      code
      msg
    }
  }
}
```

- Variables

```json
{
  "newPwd": "babababo",
  "secretKey": "migomekjgpk",
  "resToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6Imphdmc0NEBob3RtYWlsLmNvbSIsInJlZl9zZWNyZXRfa2V5IjoibWlnb21la2pncGsiLCJleHAiOjE2OTk3NTkwNDN9._xo-ABDRQf5GLfHzGzwKcFrvZT9BoqubgY0j66vTi7U"
}
```