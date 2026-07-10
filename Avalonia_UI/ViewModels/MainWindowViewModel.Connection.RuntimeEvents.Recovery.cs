using System;
using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task RecoverRuntimeStateAsync(
        string? selectWorkflowRunId = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            if (selectWorkflowRunId is null)
            {
                await LoadRunsAsync(allowWhenActionsDisabled: true);
                if (SelectedRun is not null)
                {
                    await LoadNodeRunsForSelectedRunAsync();
                }

                return;
            }

            RefreshBackgroundRunManagementContext();
            await BackgroundRunManagement.MergeRunAsync(
                selectWorkflowRunId,
                cancellationToken);
            if (string.Equals(
                    SelectedRun?.WorkflowRunId,
                    selectWorkflowRunId,
                    StringComparison.Ordinal))
            {
                await LoadNodeRunsForSelectedRunAsync();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch (Exception ex)
        {
            RuntimeEventStreamErrorMessage = ex.Message;
        }
    }
}
