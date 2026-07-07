using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;

namespace Avalonia_UI.Services;

public sealed class AvaloniaWorkflowExportFileService : IWorkflowExportFileService
{
    private static readonly FilePickerFileType WorkflowFileType = new("FlowWeaver workflow")
    {
        Patterns = ["*.flowweaver-workflow.json", "*.json"],
        MimeTypes = ["application/json"],
    };

    public async Task<WorkflowExportFileSaveResult> SaveWorkflowExportAsync(
        string suggestedFileName,
        string content,
        CancellationToken cancellationToken = default)
    {
        if (Application.Current?.ApplicationLifetime is not IClassicDesktopStyleApplicationLifetime lifetime ||
            lifetime.MainWindow is null)
        {
            return WorkflowExportFileSaveResult.Failure("Desktop window is not available.");
        }

        var storageProvider = lifetime.MainWindow.StorageProvider;
        if (!storageProvider.CanSave)
        {
            return WorkflowExportFileSaveResult.Failure("File save picker is not available.");
        }

        try
        {
            var file = await storageProvider.SaveFilePickerAsync(
                new FilePickerSaveOptions
                {
                    Title = "Export FlowWeaver workflow",
                    SuggestedFileName = suggestedFileName,
                    DefaultExtension = "json",
                    ShowOverwritePrompt = true,
                    FileTypeChoices = [WorkflowFileType],
                });

            if (file is null)
            {
                return WorkflowExportFileSaveResult.Cancel();
            }

            await using var stream = await file.OpenWriteAsync();
            await using var writer = new StreamWriter(
                stream,
                new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
            await writer.WriteAsync(content.AsMemory(), cancellationToken);
            return WorkflowExportFileSaveResult.Success(file.Name);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            return WorkflowExportFileSaveResult.Failure(ex.Message);
        }
    }
}
