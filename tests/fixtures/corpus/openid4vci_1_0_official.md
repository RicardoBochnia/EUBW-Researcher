# OpenID for Verifiable Credential Issuance 1.0

## Section 5.1 Authorization Server and access token issuance
The Credential Issuer can rely on an Authorization Server to issue the access token used at the Credential Endpoint.
When the Authorization Server is separate from the Credential Issuer, the Wallet first obtains an authorization code and then an access token from the Authorization Server.

## Section 6 Credential Endpoint
The Wallet presents the access token to the Credential Endpoint to obtain the credential.
