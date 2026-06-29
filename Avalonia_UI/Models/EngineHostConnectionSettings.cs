using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.Models;

public sealed class EngineHostConnectionSettings
{
    public const string DefaultBaseUrl = "http://127.0.0.1:8000";

    public string BaseUrl { get; init; } = DefaultBaseUrl;

    public string Token { get; init; } = string.Empty;

    public Uri BuildHealthUri()
    {
        return BuildApiUri("api/v1/health");
    }

    public Uri BuildApiUri(
        string path,
        IEnumerable<KeyValuePair<string, string?>>? query = null)
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
            Path = path.TrimStart('/'),
            Query = BuildQuery(query),
            Fragment = string.Empty,
        }.Uri;
    }

    public Uri BuildRuntimeEventsWebSocketUri()
    {
        if (string.IsNullOrWhiteSpace(Token))
        {
            throw new InvalidOperationException("EngineHost token is required.");
        }

        var apiUri = BuildApiUri(
            "ws/v1/events",
            new[] { new KeyValuePair<string, string?>("token", Token) });
        var builder = new UriBuilder(apiUri)
        {
            Scheme = apiUri.Scheme == Uri.UriSchemeHttps ? "wss" : "ws",
            Port = apiUri.Port,
        };
        return builder.Uri;
    }

    private static string BuildQuery(IEnumerable<KeyValuePair<string, string?>>? query)
    {
        if (query is null)
        {
            return string.Empty;
        }

        return string.Join(
            "&",
            query
                .Where(item => item.Value is not null)
                .Select(
                    item =>
                        $"{Uri.EscapeDataString(item.Key)}={Uri.EscapeDataString(item.Value!)}"));
    }
}
