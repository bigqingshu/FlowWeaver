using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.Models;

public sealed record SupportedLanguage(string Code, string DisplayName)
{
    public static readonly SupportedLanguage English = new("en-US", "English");

    public static readonly SupportedLanguage SimplifiedChinese = new("zh-Hans", "简体中文");

    public static IReadOnlyList<SupportedLanguage> All { get; } =
        new[] { English, SimplifiedChinese };

    public static SupportedLanguage Default => English;

    public static bool IsSupported(string? languageCode)
    {
        return Find(languageCode) is not null;
    }

    public static SupportedLanguage? Find(string? languageCode)
    {
        if (string.IsNullOrWhiteSpace(languageCode))
        {
            return null;
        }

        return All.FirstOrDefault(language =>
            string.Equals(language.Code, languageCode.Trim(), StringComparison.OrdinalIgnoreCase));
    }

    public static string NormalizeCodeOrDefault(string? languageCode)
    {
        return Find(languageCode)?.Code ?? Default.Code;
    }
}
