function Get-EC2StopFailureCategory {
  param(
    [Parameter(Mandatory=$true)][int]$ExitCode,
    [AllowEmptyString()][string]$OutputText = ""
  )

  if ($ExitCode -eq 0) { return $null }
  if ($OutputText -match "ExpiredToken|InvalidClientTokenId|AuthFailure|UnauthorizedOperation|AccessDenied") {
    return "aws_auth_or_authorization_failed"
  }
  if ($OutputText -match "RequestLimitExceeded|Throttling|TooManyRequests") { return "ec2_stop_throttled" }
  if ($OutputText -match "IncorrectInstanceState|UnsupportedOperation") { return "ec2_stop_invalid_instance_state" }
  return "ec2_stop_failed"
}
