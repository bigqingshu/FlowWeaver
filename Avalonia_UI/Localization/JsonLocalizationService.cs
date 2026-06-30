using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Localization;

public sealed class JsonLocalizationService : ILocalizationService
{
    public const string LocalizationDirectoryName = "Localization";

    private readonly string _localizationDirectory;
    private readonly Dictionary<string, string> _fallbackStrings = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _currentStrings = new(StringComparer.Ordinal);

    public JsonLocalizationService()
        : this(GetDefaultLocalizationDirectory())
    {
    }

    public JsonLocalizationService(string localizationDirectory)
    {
        _localizationDirectory = localizationDirectory;
        CurrentLanguageCode = SupportedLanguage.Default.Code;
        LoadDefaultStringsIfAvailable();
    }

    public string CurrentLanguageCode { get; private set; }

    public IReadOnlyList<SupportedLanguage> SupportedLanguages => SupportedLanguage.All;

    public static string GetDefaultLocalizationDirectory()
    {
        return Path.Combine(AppContext.BaseDirectory, LocalizationDirectoryName);
    }

    public async Task SetLanguageAsync(
        string languageCode,
        CancellationToken cancellationToken = default)
    {
        var normalizedLanguageCode = SupportedLanguage.NormalizeCodeOrDefault(languageCode);
        var fallback = await LoadLanguageFileAsync(
            SupportedLanguage.Default.Code,
            cancellationToken);
        var current = normalizedLanguageCode == SupportedLanguage.Default.Code
            ? fallback
            : await LoadLanguageFileAsync(normalizedLanguageCode, cancellationToken);

        _fallbackStrings.Clear();
        foreach (var pair in fallback)
        {
            _fallbackStrings[pair.Key] = pair.Value;
        }

        _currentStrings.Clear();
        foreach (var pair in current)
        {
            _currentStrings[pair.Key] = pair.Value;
        }

        CurrentLanguageCode = normalizedLanguageCode;
    }

    public string GetString(string key)
    {
        if (_currentStrings.TryGetValue(key, out var localized))
        {
            return localized;
        }

        return _fallbackStrings.TryGetValue(key, out var fallback)
            ? fallback
            : key;
    }

    public string Format(string key, params object?[] args)
    {
        return string.Format(
            CultureInfo.CurrentCulture,
            GetString(key),
            args);
    }

    private async Task<Dictionary<string, string>> LoadLanguageFileAsync(
        string languageCode,
        CancellationToken cancellationToken)
    {
        var path = Path.Combine(_localizationDirectory, $"{languageCode}.json");
        try
        {
            await using var stream = File.OpenRead(path);
            var strings = await JsonSerializer.DeserializeAsync<Dictionary<string, string>>(
                stream,
                cancellationToken: cancellationToken);
            return strings ?? new Dictionary<string, string>(StringComparer.Ordinal);
        }
        catch (FileNotFoundException) when (languageCode != SupportedLanguage.Default.Code)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal);
        }
        catch (DirectoryNotFoundException) when (languageCode != SupportedLanguage.Default.Code)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal);
        }
        catch (JsonException) when (languageCode != SupportedLanguage.Default.Code)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal);
        }
    }

    private void LoadDefaultStringsIfAvailable()
    {
        var path = Path.Combine(_localizationDirectory, $"{SupportedLanguage.Default.Code}.json");
        if (!File.Exists(path))
        {
            return;
        }

        try
        {
            var strings = JsonSerializer.Deserialize<Dictionary<string, string>>(
                File.ReadAllText(path));
            if (strings is null)
            {
                return;
            }

            foreach (var pair in strings)
            {
                _fallbackStrings[pair.Key] = pair.Value;
                _currentStrings[pair.Key] = pair.Value;
            }
        }
        catch (JsonException)
        {
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }
}
