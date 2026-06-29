using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class ConnectionSettingsStoreTests
{
    [TestMethod]
    public void PersistedConnectionSettingsNormalizesValidHttpUrls()
    {
        var settings = new PersistedConnectionSettings
        {
            LastSuccessfulBaseUrl = " https://engine.local:8443/root/ ",
            RecentBaseUrls = new[]
            {
                "https://engine.local:8443/root/",
                "ftp://invalid",
                "http://127.0.0.1:8000/",
            },
            UpdatedAtUtc = DateTimeOffset.Parse("2026-06-29T00:00:00Z"),
        };

        var normalized = settings.Normalized();

        Assert.AreEqual("https://engine.local:8443/root", normalized.LastSuccessfulBaseUrl);
        CollectionAssert.AreEqual(
            new[] { "https://engine.local:8443/root", "http://127.0.0.1:8000" },
            normalized.RecentBaseUrls.ToArray());
        Assert.AreEqual(PersistedConnectionSettings.CurrentSchemaVersion, normalized.SchemaVersion);
    }

    [TestMethod]
    public void PersistedConnectionSettingsFallsBackWhenAllUrlsAreInvalid()
    {
        var settings = new PersistedConnectionSettings
        {
            LastSuccessfulBaseUrl = "not a url",
            RecentBaseUrls = new[] { "ftp://invalid" },
        };

        var normalized = settings.Normalized();

        Assert.AreEqual(EngineHostConnectionSettings.DefaultBaseUrl, normalized.LastSuccessfulBaseUrl);
        CollectionAssert.AreEqual(
            new[] { EngineHostConnectionSettings.DefaultBaseUrl },
            normalized.RecentBaseUrls.ToArray());
    }

    [TestMethod]
    public void PersistedConnectionSettingsLimitsRecentUrls()
    {
        var settings = new PersistedConnectionSettings
        {
            LastSuccessfulBaseUrl = "http://host-0:8000",
            RecentBaseUrls = Enumerable
                .Range(1, 8)
                .Select(index => $"http://host-{index}:8000")
                .ToArray(),
        };

        var normalized = settings.Normalized();

        Assert.HasCount(PersistedConnectionSettings.MaxRecentBaseUrls, normalized.RecentBaseUrls);
        Assert.AreEqual("http://host-0:8000", normalized.RecentBaseUrls[0]);
    }

    [TestMethod]
    public void PersistedConnectionSettingsJsonDoesNotContainToken()
    {
        var settings = PersistedConnectionSettings.FromBaseUrl(
            "http://127.0.0.1:8000",
            DateTimeOffset.Parse("2026-06-29T00:00:00Z"));

        var json = JsonSerializer.Serialize(settings, FlowWeaverJson.Options);

        StringAssert.Contains(json, "last_successful_base_url");
        Assert.IsFalse(json.Contains("token", StringComparison.OrdinalIgnoreCase));
        Assert.IsFalse(json.Contains("authorization", StringComparison.OrdinalIgnoreCase));
    }

    [TestMethod]
    public async Task FileConnectionSettingsStoreReturnsDefaultWhenMissing()
    {
        var path = Path.Combine(CreateTempDirectory(), "connection-settings.json");
        var store = new FileConnectionSettingsStore(path);

        var settings = await store.LoadAsync();

        Assert.AreEqual(EngineHostConnectionSettings.DefaultBaseUrl, settings.LastSuccessfulBaseUrl);
    }

    [TestMethod]
    public async Task FileConnectionSettingsStoreSavesAndLoadsNormalizedSettings()
    {
        var path = Path.Combine(CreateTempDirectory(), "nested", "connection-settings.json");
        var store = new FileConnectionSettingsStore(path);
        var settings = new PersistedConnectionSettings
        {
            LastSuccessfulBaseUrl = "http://127.0.0.1:8010/",
            RecentBaseUrls = new[] { "http://127.0.0.1:8010/", "https://engine.local" },
            UpdatedAtUtc = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };

        await store.SaveAsync(settings);
        var loaded = await store.LoadAsync();

        Assert.AreEqual("http://127.0.0.1:8010", loaded.LastSuccessfulBaseUrl);
        CollectionAssert.AreEqual(
            new[] { "http://127.0.0.1:8010", "https://engine.local" },
            loaded.RecentBaseUrls.ToArray());
        Assert.AreEqual(DateTimeOffset.Parse("2026-06-29T01:02:03Z"), loaded.UpdatedAtUtc);
    }

    [TestMethod]
    public async Task FileConnectionSettingsStoreReturnsDefaultForCorruptJson()
    {
        var path = Path.Combine(CreateTempDirectory(), "connection-settings.json");
        await File.WriteAllTextAsync(path, "{ not-json");
        var store = new FileConnectionSettingsStore(path);

        var settings = await store.LoadAsync();

        Assert.AreEqual(EngineHostConnectionSettings.DefaultBaseUrl, settings.LastSuccessfulBaseUrl);
    }

    [TestMethod]
    public void FileConnectionSettingsStoreDefaultPathUsesLocalApplicationData()
    {
        var path = FileConnectionSettingsStore.GetDefaultSettingsPath();

        StringAssert.Contains(path, "FlowWeaver");
        StringAssert.Contains(path, "Avalonia_UI");
        Assert.AreEqual(FileConnectionSettingsStore.SettingsFileName, Path.GetFileName(path));
    }

    private static string CreateTempDirectory()
    {
        var directory = Path.Combine(Path.GetTempPath(), "FlowWeaverTests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        return directory;
    }
}
