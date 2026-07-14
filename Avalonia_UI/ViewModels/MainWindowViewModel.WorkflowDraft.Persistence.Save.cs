using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task<bool> TrySaveWorkflowDefinitionDraftAsync()
    {
        if (!FlushPendingNodeConfigAutoSave())
        {
            return false;
        }

        if (WorkflowDefinitionDetail is null)
        {
            RejectWorkflowDefinitionSaveWithoutDetail();
            return false;
        }

        if (!TryReadWorkflowDefinitionDraftJsonForSave(out var definition))
        {
            return false;
        }

        BeginWorkflowDefinitionDraftSave();

        try
        {
            var saved = await _apiClient.UpdateWorkflowAsync(
                BuildSettings(),
                WorkflowDefinitionDetail.WorkflowId,
                WorkflowDefinitionDetail.Name,
                definition,
                WorkflowDefinitionDetail.RevisionId,
                _shutdown.Token);

            if (saved.Ok && saved.Data is not null)
            {
                await ApplyWorkflowDefinitionDraftSaveSuccessAsync(saved.Data);
                return true;
            }

            if (saved.Error?.ErrorCode == "WORKFLOW_REVISION_CONFLICT")
            {
                ApplyWorkflowDefinitionDraftRevisionConflictSaveFailure();
                return false;
            }

            ApplyWorkflowDefinitionDraftSaveFailure(saved);
            return false;
        }
        finally
        {
            CompleteWorkflowDefinitionDraftSave();
        }
    }
}
