using System;
using System.Text.Json.Serialization;

namespace Avalonia_UI.Models;

public sealed class PersistedUiSettings
{
    public const int CurrentSchemaVersion = 1;

    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; init; } = CurrentSchemaVersion;

    [JsonPropertyName("language_code")]
    public string LanguageCode { get; init; } = SupportedLanguage.Default.Code;

    [JsonPropertyName("updated_at_utc")]
    public DateTimeOffset UpdatedAtUtc { get; init; } = DateTimeOffset.UtcNow;

    public static PersistedUiSettings Default()
    {
        return FromLanguageCode(SupportedLanguage.Default.Code);
    }

    public static PersistedUiSettings FromLanguageCode(
        string? languageCode,
        DateTimeOffset? updatedAtUtc = null)
    {
        return new PersistedUiSettings
        {
            LanguageCode = SupportedLanguage.NormalizeCodeOrDefault(languageCode),
            UpdatedAtUtc = updatedAtUtc ?? DateTimeOffset.UtcNow,
        };
    }

    public PersistedUiSettings Normalized()
    {
        return new PersistedUiSettings
        {
            SchemaVersion = CurrentSchemaVersion,
            LanguageCode = SupportedLanguage.NormalizeCodeOrDefault(LanguageCode),
            UpdatedAtUtc = UpdatedAtUtc,
        };
    }
}
