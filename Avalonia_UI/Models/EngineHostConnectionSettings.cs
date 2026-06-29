using System;

namespace Avalonia_UI.Models;

public sealed class EngineHostConnectionSettings
{
    public const string DefaultBaseUrl = "http://127.0.0.1:8000";

    public string BaseUrl { get; init; } = DefaultBaseUrl;

    public string Token { get; init; } = string.Empty;

    public Uri BuildHealthUri()
    {
        var trimmedBaseUrl = BaseUrl.Trim();
        if (string.IsNullOrWhiteSpace(trimmedBaseUrl))
        {
            throw new InvalidOperationException("EngineHost base URL is required.");
        }

        if (!Uri.TryCreate(trimmedBaseUrl, UriKind.Absolute, out var baseUri))
        {
            throw new InvalidOperationException("EngineHost base URL must be an absolute URL.");
        }

        if (baseUri.Scheme != Uri.UriSchemeHttp && baseUri.Scheme != Uri.UriSchemeHttps)
        {
            throw new InvalidOperationException("EngineHost base URL must use HTTP or HTTPS.");
        }

        return new UriBuilder(baseUri)
        {
            Path = "api/v1/health",
            Query = string.Empty,
            Fragment = string.Empty,
        }.Uri;
    }
}
