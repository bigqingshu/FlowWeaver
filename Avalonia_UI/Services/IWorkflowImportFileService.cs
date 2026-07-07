using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.Services;

public interface IWorkflowImportFileService
{
    Task<WorkflowImportFileOpenResult> OpenWorkflowImportAsync(
        CancellationToken cancellationToken = default);
}

public sealed record WorkflowImportFileOpenResult(
    bool Opened,
    bool Cancelled,
    string? FileName,
    string? Content,
    string? ErrorMessage)
{
    public static WorkflowImportFileOpenResult Success(string? fileName, string content)
    {
        return new WorkflowImportFileOpenResult(true, false, fileName, content, null);
    }

    public static WorkflowImportFileOpenResult Cancel()
    {
        return new WorkflowImportFileOpenResult(false, true, null, null, null);
    }

    public static WorkflowImportFileOpenResult Failure(string errorMessage)
    {
        return new WorkflowImportFileOpenResult(false, false, null, null, errorMessage);
    }
}
