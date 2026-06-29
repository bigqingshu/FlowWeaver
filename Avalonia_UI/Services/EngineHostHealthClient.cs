using System;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class EngineHostHealthClient
{
    private readonly IEngineHostApiClient _apiClient;

    public EngineHostHealthClient()
        : this(new EngineHostApiClient())
    {
    }

    public EngineHostHealthClient(HttpClient httpClient)
        : this(new EngineHostApiClient(httpClient))
    {
    }

    public EngineHostHealthClient(IEngineHostApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    public async Task<EngineHostHealthCheckResult> CheckAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        try
        {
            settings.BuildHealthUri();
        }
        catch (InvalidOperationException ex)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", ex.Message);
        }

        try
        {
            var envelope = await _apiClient.GetHealthAsync(settings, cancellationToken);
            if (envelope.Ok && envelope.Data?.Status == "ok")
            {
                return new EngineHostHealthCheckResult(true, "EngineHost health check passed.");
            }

            return new EngineHostHealthCheckResult(
                false,
                "Connection failed.",
                envelope.Error?.Message ?? "EngineHost health response was not recognized.");
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", "Connection timed out.");
        }
        catch (HttpRequestException ex)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", ex.Message);
        }
    }
}
