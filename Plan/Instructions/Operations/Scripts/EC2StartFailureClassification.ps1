function Get-EC2StartFailureCategory {
  param(
    [Parameter(Mandatory=$true)][int]$ExitCode,
    [AllowEmptyString()][string]$OutputText = ""
  )

  if ($ExitCode -eq 0) { return $null }
  if ($OutputText -match "InsufficientInstanceCapacity") { return "ec2_insufficient_instance_capacity" }
  if ($OutputText -match "ExpiredToken|InvalidClientTokenId|AuthFailure|UnauthorizedOperation|AccessDenied") {
    return "aws_auth_or_authorization_failed"
  }
  if ($OutputText -match "RequestLimitExceeded|Throttling|TooManyRequests") { return "ec2_start_throttled" }
  return "ec2_start_failed"
}
