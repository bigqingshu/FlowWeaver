using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.Services;

public interface IWorkflowExportFileService
{
    Task<WorkflowExportFileSaveResult> SaveWorkflowExportAsync(
        string suggestedFileName,
        string content,
        CancellationToken cancellationToken = default);
}

public sealed record WorkflowExportFileSaveResult(
    bool Saved,
    bool Cancelled,
    string? FileName,
    string? ErrorMessage)
{
    public static WorkflowExportFileSaveResult Success(string? fileName)
    {
        return new WorkflowExportFileSaveResult(true, false, fileName, null);
    }

    public static WorkflowExportFileSaveResult Cancel()
    {
        return new WorkflowExportFileSaveResult(false, true, null, null);
    }

    public static WorkflowExportFileSaveResult Failure(string errorMessage)
    {
        return new WorkflowExportFileSaveResult(false, false, null, errorMessage);
    }
}
