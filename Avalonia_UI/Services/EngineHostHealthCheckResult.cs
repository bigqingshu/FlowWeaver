namespace Avalonia_UI.Services;

public sealed record EngineHostHealthCheckResult(
    bool IsHealthy,
    string Message,
    string? ErrorMessage = null);
