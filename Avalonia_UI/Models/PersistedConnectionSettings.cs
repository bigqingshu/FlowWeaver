using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

namespace Avalonia_UI.Models;

public sealed class PersistedConnectionSettings
{
    public const int CurrentSchemaVersion = 1;
    public const int MaxRecentBaseUrls = 5;

    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; init; } = CurrentSchemaVersion;

    [JsonPropertyName("last_successful_base_url")]
    public string LastSuccessfulBaseUrl { get; init; } =
        EngineHostConnectionSettings.DefaultBaseUrl;

    [JsonPropertyName("recent_base_urls")]
    public IReadOnlyList<string> RecentBaseUrls { get; init; } =
        new[] { EngineHostConnectionSettings.DefaultBaseUrl };

    [JsonPropertyName("updated_at_utc")]
    public DateTimeOffset UpdatedAtUtc { get; init; } = DateTimeOffset.UtcNow;

    public static PersistedConnectionSettings Default()
    {
        return FromBaseUrl(EngineHostConnectionSettings.DefaultBaseUrl);
    }

    public static PersistedConnectionSettings FromBaseUrl(
        string baseUrl,
        DateTimeOffset? updatedAtUtc = null)
    {
        var normalizedBaseUrl = NormalizeBaseUrl(baseUrl)
            ?? EngineHostConnectionSettings.DefaultBaseUrl;
        return new PersistedConnectionSettings
        {
            LastSuccessfulBaseUrl = normalizedBaseUrl,
            RecentBaseUrls = new[] { normalizedBaseUrl },
            UpdatedAtUtc = updatedAtUtc ?? DateTimeOffset.UtcNow,
        };
    }

    public PersistedConnectionSettings Normalized()
    {
        var normalizedUrls = RecentBaseUrls
            .Prepend(LastSuccessfulBaseUrl)
            .Select(NormalizeBaseUrl)
            .Where(url => url is not null)
            .Select(url => url!)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(MaxRecentBaseUrls)
            .ToArray();

        if (normalizedUrls.Length == 0)
        {
            normalizedUrls = new[] { EngineHostConnectionSettings.DefaultBaseUrl };
        }

        return new PersistedConnectionSettings
        {
            SchemaVersion = CurrentSchemaVersion,
            LastSuccessfulBaseUrl = normalizedUrls[0],
            RecentBaseUrls = normalizedUrls,
            UpdatedAtUtc = UpdatedAtUtc,
        };
    }

    private static string? NormalizeBaseUrl(string? baseUrl)
    {
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            return null;
        }

        var trimmed = baseUrl.Trim();
        if (!Uri.TryCreate(trimmed, UriKind.Absolute, out var uri))
        {
            return null;
        }

        if (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps)
        {
            return null;
        }

        return new UriBuilder(uri)
        {
            Path = uri.AbsolutePath == "/"
                ? string.Empty
                : uri.AbsolutePath.TrimEnd('/'),
            Query = string.Empty,
            Fragment = string.Empty,
        }.Uri.ToString().TrimEnd('/');
    }
}
