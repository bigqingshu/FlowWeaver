using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Localization;

public interface ILocalizationService
{
    string CurrentLanguageCode { get; }

    IReadOnlyList<SupportedLanguage> SupportedLanguages { get; }

    Task SetLanguageAsync(
        string languageCode,
        CancellationToken cancellationToken = default);

    string GetString(string key);

    string Format(string key, params object?[] args);
}
