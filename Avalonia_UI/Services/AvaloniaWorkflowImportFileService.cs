using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;

namespace Avalonia_UI.Services;

public sealed class AvaloniaWorkflowImportFileService : IWorkflowImportFileService
{
    private static readonly FilePickerFileType WorkflowFileType = new("FlowWeaver workflow")
    {
        Patterns = ["*.flowweaver-workflow.json", "*.json"],
        MimeTypes = ["application/json"],
    };

    public async Task<WorkflowImportFileOpenResult> OpenWorkflowImportAsync(
        CancellationToken cancellationToken = default)
    {
        if (Application.Current?.ApplicationLifetime is not IClassicDesktopStyleApplicationLifetime lifetime ||
            lifetime.MainWindow is null)
        {
            return WorkflowImportFileOpenResult.Failure("Desktop window is not available.");
        }

        var storageProvider = lifetime.MainWindow.StorageProvider;
        if (!storageProvider.CanOpen)
        {
            return WorkflowImportFileOpenResult.Failure("File open picker is not available.");
        }

        try
        {
            var files = await storageProvider.OpenFilePickerAsync(
                new FilePickerOpenOptions
                {
                    Title = "Import FlowWeaver workflow",
                    AllowMultiple = false,
                    FileTypeFilter = [WorkflowFileType],
                });
            var file = files.FirstOrDefault();
            if (file is null)
            {
                return WorkflowImportFileOpenResult.Cancel();
            }

            await using var stream = await file.OpenReadAsync();
            using var reader = new StreamReader(
                stream,
                Encoding.UTF8,
                detectEncodingFromByteOrderMarks: true);
            var content = await reader.ReadToEndAsync(cancellationToken);
            return WorkflowImportFileOpenResult.Success(file.Name, content);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            return WorkflowImportFileOpenResult.Failure(ex.Message);
        }
    }
}
