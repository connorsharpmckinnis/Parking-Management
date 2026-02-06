# =============================================================================
# Parking Management - Build and Push Script
# =============================================================================
# Builds all container images and pushes them to DockerHub.
#
# Usage:
#   .\build-and-push.ps1                    # Build and push all images
#   .\build-and-push.ps1 -Tag v1.0.0        # Use specific tag (also pushes 'latest')
#   .\build-and-push.ps1 -SkipPush          # Build only, don't push
#   .\build-and-push.ps1 -Services control-plane,dashboard  # Build specific services
#
# Prerequisites:
#   - Docker Desktop running
#   - Logged into DockerHub: docker login
# =============================================================================

param(
    [string]$DockerHubUsername = "connorsharpmckinnis",
    [string]$Tag = "latest",
    [switch]$SkipPush,
    [string[]]$Services
)

# Define all services and their build contexts
$AllServices = @{
    "control-plane" = @{
        Context = "."
        Dockerfile = "control_plane/Dockerfile"
        ImageName = "peakpark-control-plane"
    }
    "ingest-service" = @{
        Context = "."
        Dockerfile = "ingest_service/Dockerfile"
        ImageName = "peakpark-ingest-service"
    }
    "dashboard" = @{
        Context = "."
        Dockerfile = "dashboard/Dockerfile"
        ImageName = "peakpark-dashboard"
    }
    "orchestrator" = @{
        Context = "."
        Dockerfile = "orchestrator/Dockerfile"
        ImageName = "peakpark-orchestrator"
    }
    "vision-worker" = @{
        Context = "."
        Dockerfile = "vision_worker/Dockerfile"
        ImageName = "peakpark-vision-worker"
    }
    "mqtt-broker" = @{
        Context = "mqtt_broker"
        Dockerfile = "Dockerfile"
        ImageName = "peakpark-mqtt-broker"
    }
    "edge-simulator" = @{
        Context = "edge_processing"
        Dockerfile = "Dockerfile"
        ImageName = "peakpark-edge-simulator"
    }
    "ingest-bridge" = @{
        Context = "ingest_bridge"
        Dockerfile = "Dockerfile"
        ImageName = "peakpark-ingest-bridge"
    }
}

# Determine which services to build
if ($Services) {
    $ServicesToBuild = $Services
} else {
    $ServicesToBuild = $AllServices.Keys
}

# Validate DockerHub username
if ($DockerHubUsername -eq "__REPLACE_ME__") {
    Write-Host ""
    Write-Host "ERROR: DockerHub username not configured!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please either:" -ForegroundColor Yellow
    Write-Host "  1. Edit this script and set `$DockerHubUsername to your username" -ForegroundColor Yellow
    Write-Host "  2. Run with: .\build-and-push.ps1 -DockerHubUsername yourusername" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " PeakPark - Build & Push Pipeline" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " DockerHub: $DockerHubUsername" -ForegroundColor White
Write-Host " Tag:       $Tag" -ForegroundColor White
Write-Host " Push:      $(-not $SkipPush)" -ForegroundColor White
Write-Host " Services:  $($ServicesToBuild -join ', ')" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Track results
$results = @{}
$startTime = Get-Date

foreach ($serviceName in $ServicesToBuild) {
    if (-not $AllServices.ContainsKey($serviceName)) {
        Write-Host "WARNING: Unknown service '$serviceName', skipping..." -ForegroundColor Yellow
        continue
    }

    $service = $AllServices[$serviceName]
    $fullImageName = "$DockerHubUsername/$($service.ImageName)"
        
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Write-Host "Building: $serviceName" -ForegroundColor Green
    Write-Host "  Image:  $fullImageName`:$Tag" -ForegroundColor White
    
    # Build the image
    $buildArgs = @(
        "build",
        "-t", "${fullImageName}:${Tag}",
        "-f", "$($service.Context)/$($service.Dockerfile)"
    )
    
    # Also tag as latest if not already
    if ($Tag -ne "latest") {
        $buildArgs += "-t"
        $buildArgs += "${fullImageName}:latest"
    }
    
    $buildArgs += $service.Context
    
    $buildResult = & docker @buildArgs 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED to build!" -ForegroundColor Red
        $results[$serviceName] = "BUILD_FAILED"
        continue
    }
    
    Write-Host "  Built successfully" -ForegroundColor Green
    
    if (-not $SkipPush) {
        Write-Host "  Pushing..." -ForegroundColor Cyan
        
        # Push the tagged version
        docker push "${fullImageName}:${Tag}" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAILED to push!" -ForegroundColor Red
            $results[$serviceName] = "PUSH_FAILED"
            continue
        }
        
        # Also push latest if we used a version tag
        if ($Tag -ne "latest") {
            docker push "${fullImageName}:latest" 2>&1 | Out-Null
        }
        
        Write-Host "  Pushed successfully" -ForegroundColor Green
        $results[$serviceName] = "SUCCESS"
    } else {
        Write-Host "  Skipped push (--SkipPush)" -ForegroundColor Yellow
        $results[$serviceName] = "BUILT_ONLY"
    }
}

# Summary
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Build Summary" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Duration: $($duration.TotalSeconds.ToString('F1')) seconds" -ForegroundColor White
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($serviceName in $results.Keys | Sort-Object) {
    $status = $results[$serviceName]
    switch ($status) {
        "SUCCESS" { 
            Write-Host " [OK] $serviceName" -ForegroundColor Green
            $successCount++
        }
        "BUILT_ONLY" { 
            Write-Host " [OK] $serviceName (built, not pushed)" -ForegroundColor Yellow
            $successCount++
        }
        "BUILD_FAILED" { 
            Write-Host " [X]  $serviceName (build failed)" -ForegroundColor Red
            $failCount++
        }
        "PUSH_FAILED" { 
            Write-Host " [X]  $serviceName (push failed)" -ForegroundColor Red
            $failCount++
        }
    }
}

Write-Host ""
Write-Host " Total: $successCount succeeded, $failCount failed" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

if ($failCount -gt 0) {
    exit 1
}
