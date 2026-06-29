using System;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class FileConnectionSettingsStore : IConnectionSettingsStore
{
    public const string SettingsFileName = "connection-settings.json";

    private readonly string _settingsPath;

    public FileConnectionSettingsStore()
        : this(GetDefaultSettingsPath())
    {
    }

    public FileConnectionSettingsStore(string settingsPath)
    {
        _settingsPath = settingsPath;
    }

    public string SettingsPath => _settingsPath;

    public static string GetDefaultSettingsPath()
    {
        var localApplicationData = Environment.GetFolderPath(
            Environment.SpecialFolder.LocalApplicationData);
        return Path.Combine(
            localApplicationData,
            "FlowWeaver",
            "Avalonia_UI",
            SettingsFileName);
    }

    public async Task<PersistedConnectionSettings> LoadAsync(
        CancellationToken cancellationToken = default)
    {
        if (!File.Exists(_settingsPath))
        {
            return PersistedConnectionSettings.Default();
        }

        try
        {
            await using var stream = File.OpenRead(_settingsPath);
            var settings = await JsonSerializer.DeserializeAsync<PersistedConnectionSettings>(
                stream,
                FlowWeaverJson.Options,
                cancellationToken);
            return (settings ?? PersistedConnectionSettings.Default()).Normalized();
        }
        catch (JsonException)
        {
            return PersistedConnectionSettings.Default();
        }
        catch (IOException)
        {
            return PersistedConnectionSettings.Default();
        }
        catch (UnauthorizedAccessException)
        {
            return PersistedConnectionSettings.Default();
        }
    }

    public async Task SaveAsync(
        PersistedConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        var normalized = settings.Normalized();
        var directory = Path.GetDirectoryName(_settingsPath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        await using var stream = File.Create(_settingsPath);
        await JsonSerializer.SerializeAsync(
            stream,
            normalized,
            FlowWeaverJson.Options,
            cancellationToken);
    }
}
