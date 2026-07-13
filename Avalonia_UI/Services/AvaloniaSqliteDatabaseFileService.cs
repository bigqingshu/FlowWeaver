using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;

namespace Avalonia_UI.Services;

public sealed class AvaloniaSqliteDatabaseFileService : ISqliteDatabaseFileService
{
    private static readonly FilePickerFileType SqliteFileType = new("SQLite database")
    {
        Patterns = ["*.db", "*.sqlite", "*.sqlite3", "*.db3"],
        MimeTypes = ["application/vnd.sqlite3", "application/x-sqlite3"],
    };

    public async Task<SqliteDatabaseFileOpenResult> OpenDatabaseAsync(
        CancellationToken cancellationToken = default)
    {
        if (Application.Current?.ApplicationLifetime is not
                IClassicDesktopStyleApplicationLifetime lifetime
            || lifetime.MainWindow is null)
        {
            return SqliteDatabaseFileOpenResult.Failure(
                "Desktop window is not available.");
        }

        var storageProvider = lifetime.MainWindow.StorageProvider;
        if (!storageProvider.CanOpen)
        {
            return SqliteDatabaseFileOpenResult.Failure(
                "File open picker is not available.");
        }

        try
        {
            var files = await storageProvider.OpenFilePickerAsync(
                new FilePickerOpenOptions
                {
                    Title = "Open SQLite database",
                    AllowMultiple = false,
                    FileTypeFilter = [SqliteFileType, FilePickerFileTypes.All],
                });
            var file = files.FirstOrDefault();
            if (file is null)
            {
                return SqliteDatabaseFileOpenResult.Cancel();
            }

            var localPath = file.TryGetLocalPath();
            return string.IsNullOrWhiteSpace(localPath)
                ? SqliteDatabaseFileOpenResult.Failure(
                    "The selected file does not expose a local path.")
                : SqliteDatabaseFileOpenResult.Success(localPath);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            return SqliteDatabaseFileOpenResult.Failure(ex.Message);
        }
    }
}
