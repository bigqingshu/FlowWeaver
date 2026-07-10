using System;
using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly Func<CancellationToken, Task> _workflowDraftJsonDebounceDelay;
    private CancellationTokenSource? advancedWorkflowDraftJsonDebounceCancellation;
    private bool isSynchronizingAdvancedWorkflowDraftJson;
    private int advancedWorkflowDraftJsonRevision;

    private void SynchronizeAdvancedWorkflowDraftJson(string value)
    {
        if (string.Equals(
                AdvancedWorkflowDefinitionDraftJson,
                value,
                StringComparison.Ordinal))
        {
            return;
        }

        isSynchronizingAdvancedWorkflowDraftJson = true;
        try
        {
            AdvancedWorkflowDefinitionDraftJson = value;
        }
        finally
        {
            isSynchronizingAdvancedWorkflowDraftJson = false;
        }
    }

    private void ScheduleAdvancedWorkflowDraftJsonApply(string value)
    {
        advancedWorkflowDraftJsonDebounceCancellation?.Cancel();
        advancedWorkflowDraftJsonDebounceCancellation?.Dispose();
        advancedWorkflowDraftJsonDebounceCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var cancellationToken = advancedWorkflowDraftJsonDebounceCancellation.Token;
        var revision = ++advancedWorkflowDraftJsonRevision;
        _ = ApplyAdvancedWorkflowDraftJsonAfterDelayAsync(
            value,
            revision,
            cancellationToken);
    }

    private async Task ApplyAdvancedWorkflowDraftJsonAfterDelayAsync(
        string value,
        int revision,
        CancellationToken cancellationToken)
    {
        try
        {
            await _workflowDraftJsonDebounceDelay(cancellationToken);
            cancellationToken.ThrowIfCancellationRequested();
            if (revision != advancedWorkflowDraftJsonRevision)
            {
                return;
            }

            WorkflowDefinitionDraftJson = value;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
    }
}
