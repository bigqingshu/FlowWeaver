using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class UiSettingsStoreTests
{
    [TestMethod]
    public void SupportedLanguageNormalizesKnownLanguageCodes()
    {
        Assert.AreEqual("en-US", SupportedLanguage.NormalizeCodeOrDefault("EN-us"));
        Assert.AreEqual("zh-Hans", SupportedLanguage.NormalizeCodeOrDefault(" zh-Hans "));
    }

    [TestMethod]
    public void SupportedLanguageFallsBackForUnsupportedLanguageCodes()
    {
        Assert.AreEqual("en-US", SupportedLanguage.NormalizeCodeOrDefault("fr-FR"));
        Assert.AreEqual("en-US", SupportedLanguage.NormalizeCodeOrDefault(""));
    }

    [TestMethod]
    public void PersistedUiSettingsNormalizesInvalidLanguageCode()
    {
        var settings = new PersistedUiSettings
        {
            LanguageCode = "fr-FR",
            ThemeVariant = "dark",
            UpdatedAtUtc = DateTimeOffset.Parse("2026-06-30T01:02:03Z"),
        };

        var normalized = settings.Normalized();

        Assert.AreEqual(PersistedUiSettings.CurrentSchemaVersion, normalized.SchemaVersion);
        Assert.AreEqual("en-US", normalized.LanguageCode);
        Assert.AreEqual("Dark", normalized.ThemeVariant);
        Assert.AreEqual(DateTimeOffset.Parse("2026-06-30T01:02:03Z"), normalized.UpdatedAtUtc);
    }

    [TestMethod]
    public void PersistedUiSettingsNormalizesInvalidThemeVariant()
    {
        Assert.AreEqual("Light", PersistedUiSettings.NormalizeThemeVariantOrDefault(" light "));
        Assert.AreEqual("Dark", PersistedUiSettings.NormalizeThemeVariantOrDefault("DARK"));
        Assert.AreEqual("System", PersistedUiSettings.NormalizeThemeVariantOrDefault("System"));
        Assert.AreEqual("System", PersistedUiSettings.NormalizeThemeVariantOrDefault("midnight"));
        Assert.AreEqual("System", PersistedUiSettings.NormalizeThemeVariantOrDefault(""));
    }

    [TestMethod]
    public void PersistedUiSettingsJsonDoesNotContainConnectionData()
    {
        var settings = PersistedUiSettings.FromLanguageCode(
            "zh-Hans",
            DateTimeOffset.Parse("2026-06-30T00:00:00Z"));

        var json = JsonSerializer.Serialize(settings, FlowWeaverJson.Options);

        StringAssert.Contains(json, "language_code");
        StringAssert.Contains(json, "theme_variant");
        Assert.IsFalse(json.Contains("token", StringComparison.OrdinalIgnoreCase));
        Assert.IsFalse(json.Contains("base_url", StringComparison.OrdinalIgnoreCase));
        Assert.IsFalse(json.Contains("authorization", StringComparison.OrdinalIgnoreCase));
    }

    [TestMethod]
    public async Task FileUiSettingsStoreReturnsDefaultWhenMissing()
    {
        var path = Path.Combine(CreateTempDirectory(), "ui-settings.json");
        var store = new FileUiSettingsStore(path);

        var settings = await store.LoadAsync();

        Assert.AreEqual("en-US", settings.LanguageCode);
        Assert.AreEqual("System", settings.ThemeVariant);
    }

    [TestMethod]
    public async Task FileUiSettingsStoreSavesAndLoadsNormalizedSettings()
    {
        var path = Path.Combine(CreateTempDirectory(), "nested", "ui-settings.json");
        var store = new FileUiSettingsStore(path);
        var settings = PersistedUiSettings.FromSettings(
            "zh-Hans",
            "Dark",
            DateTimeOffset.Parse("2026-06-30T01:02:03Z"));

        await store.SaveAsync(settings);
        var loaded = await store.LoadAsync();

        Assert.AreEqual("zh-Hans", loaded.LanguageCode);
        Assert.AreEqual("Dark", loaded.ThemeVariant);
        Assert.AreEqual(DateTimeOffset.Parse("2026-06-30T01:02:03Z"), loaded.UpdatedAtUtc);
    }

    [TestMethod]
    public async Task FileUiSettingsStoreReturnsDefaultForCorruptJson()
    {
        var path = Path.Combine(CreateTempDirectory(), "ui-settings.json");
        await File.WriteAllTextAsync(path, "{ not-json");
        var store = new FileUiSettingsStore(path);

        var settings = await store.LoadAsync();

        Assert.AreEqual("en-US", settings.LanguageCode);
        Assert.AreEqual("System", settings.ThemeVariant);
    }

    [TestMethod]
    public async Task FileUiSettingsStoreReturnsDefaultForUnsupportedLanguage()
    {
        var path = Path.Combine(CreateTempDirectory(), "ui-settings.json");
        await File.WriteAllTextAsync(
            path,
            """
            {
              "schema_version": 1,
              "language_code": "fr-FR",
              "theme_variant": "not-a-theme",
              "updated_at_utc": "2026-06-30T00:00:00Z"
            }
            """);
        var store = new FileUiSettingsStore(path);

        var settings = await store.LoadAsync();

        Assert.AreEqual("en-US", settings.LanguageCode);
        Assert.AreEqual("System", settings.ThemeVariant);
    }

    [TestMethod]
    public void FileUiSettingsStoreDefaultPathUsesLocalApplicationData()
    {
        var path = FileUiSettingsStore.GetDefaultSettingsPath();

        StringAssert.Contains(path, "FlowWeaver");
        StringAssert.Contains(path, "Avalonia_UI");
        Assert.AreEqual(FileUiSettingsStore.SettingsFileName, Path.GetFileName(path));
    }

    private static string CreateTempDirectory()
    {
        var directory = Path.Combine(
            Path.GetTempPath(),
            "FlowWeaverTests",
            Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        return directory;
    }
}
