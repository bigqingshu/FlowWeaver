using System;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class FileUiSettingsStore : IUiSettingsStore
{
    public const string SettingsFileName = "ui-settings.json";

    private readonly string _settingsPath;

    public FileUiSettingsStore()
        : this(GetDefaultSettingsPath())
    {
    }

    public FileUiSettingsStore(string settingsPath)
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

    public async Task<PersistedUiSettings> LoadAsync(
        CancellationToken cancellationToken = default)
    {
        if (!File.Exists(_settingsPath))
        {
            return PersistedUiSettings.Default();
        }

        try
        {
            await using var stream = File.OpenRead(_settingsPath);
            var settings = await JsonSerializer.DeserializeAsync<PersistedUiSettings>(
                stream,
                FlowWeaverJson.Options,
                cancellationToken);
            return (settings ?? PersistedUiSettings.Default()).Normalized();
        }
        catch (JsonException)
        {
            return PersistedUiSettings.Default();
        }
        catch (IOException)
        {
            return PersistedUiSettings.Default();
        }
        catch (UnauthorizedAccessException)
        {
            return PersistedUiSettings.Default();
        }
    }

    public async Task SaveAsync(
        PersistedUiSettings settings,
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
