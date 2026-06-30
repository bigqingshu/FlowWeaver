using System;
using System.Text.Json.Serialization;

namespace Avalonia_UI.Models;

public sealed class PersistedUiSettings
{
    public const int CurrentSchemaVersion = 1;
    public const string LightThemeVariant = "Light";
    public const string DarkThemeVariant = "Dark";
    public const string SystemThemeVariant = "System";

    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; init; } = CurrentSchemaVersion;

    [JsonPropertyName("language_code")]
    public string LanguageCode { get; init; } = SupportedLanguage.Default.Code;

    [JsonPropertyName("theme_variant")]
    public string ThemeVariant { get; init; } = "System";

    [JsonPropertyName("updated_at_utc")]
    public DateTimeOffset UpdatedAtUtc { get; init; } = DateTimeOffset.UtcNow;

    public static PersistedUiSettings Default()
    {
        return FromSettings(SupportedLanguage.Default.Code, SystemThemeVariant);
    }

    public static PersistedUiSettings FromSettings(
        string? languageCode,
        string? themeVariant,
        DateTimeOffset? updatedAtUtc = null)
    {
        return new PersistedUiSettings
        {
            LanguageCode = SupportedLanguage.NormalizeCodeOrDefault(languageCode),
            ThemeVariant = NormalizeThemeVariantOrDefault(themeVariant),
            UpdatedAtUtc = updatedAtUtc ?? DateTimeOffset.UtcNow,
        };
    }

    public static PersistedUiSettings FromLanguageCode(
        string? languageCode,
        DateTimeOffset? updatedAtUtc = null)
    {
        return FromSettings(languageCode, "System", updatedAtUtc);
    }

    public PersistedUiSettings Normalized()
    {
        return new PersistedUiSettings
        {
            SchemaVersion = CurrentSchemaVersion,
            LanguageCode = SupportedLanguage.NormalizeCodeOrDefault(LanguageCode),
            ThemeVariant = NormalizeThemeVariantOrDefault(ThemeVariant),
            UpdatedAtUtc = UpdatedAtUtc,
        };
    }

    public static string NormalizeThemeVariantOrDefault(string? themeVariant)
    {
        return themeVariant?.Trim().ToUpperInvariant() switch
        {
            "LIGHT" => LightThemeVariant,
            "DARK" => DarkThemeVariant,
            "SYSTEM" => SystemThemeVariant,
            _ => SystemThemeVariant,
        };
    }
}
