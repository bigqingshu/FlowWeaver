using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class EngineHostHealthClient
{
    private readonly HttpClient _httpClient;

    public EngineHostHealthClient()
        : this(new HttpClient { Timeout = TimeSpan.FromSeconds(5) })
    {
    }

    public EngineHostHealthClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<EngineHostHealthCheckResult> CheckAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        Uri healthUri;
        try
        {
            healthUri = settings.BuildHealthUri();
        }
        catch (InvalidOperationException ex)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", ex.Message);
        }

        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, healthUri);
            using var response = await _httpClient.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken);
            var body = await response.Content.ReadAsStringAsync(cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                return new EngineHostHealthCheckResult(
                    false,
                    "Connection failed.",
                    $"EngineHost returned {(int)response.StatusCode} {response.ReasonPhrase}.");
            }

            if (IsHealthyEnvelope(body))
            {
                return new EngineHostHealthCheckResult(true, "EngineHost health check passed.");
            }

            return new EngineHostHealthCheckResult(
                false,
                "Connection failed.",
                "EngineHost health response was not recognized.");
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", "Connection timed out.");
        }
        catch (HttpRequestException ex)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", ex.Message);
        }
        catch (JsonException ex)
        {
            return new EngineHostHealthCheckResult(false, "Connection failed.", ex.Message);
        }
    }

    private static bool IsHealthyEnvelope(string body)
    {
        using var document = JsonDocument.Parse(body);
        var root = document.RootElement;

        if (!root.TryGetProperty("ok", out var okElement)
            || okElement.ValueKind != JsonValueKind.True)
        {
            return false;
        }

        if (!root.TryGetProperty("data", out var dataElement)
            || dataElement.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        return dataElement.TryGetProperty("status", out var statusElement)
            && statusElement.ValueKind == JsonValueKind.String
            && statusElement.GetString() == "ok";
    }
}
