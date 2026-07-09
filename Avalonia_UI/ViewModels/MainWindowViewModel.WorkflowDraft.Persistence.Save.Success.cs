using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private async Task ApplyWorkflowDefinitionDraftSaveSuccessAsync(
        WorkflowDefinitionDto savedWorkflowDefinition)
    {
        WorkflowDefinitionValidationMessage =
            F(
                "format.saved_workflow",
                savedWorkflowDefinition.Name,
                savedWorkflowDefinition.Version);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.save",
            UiNotificationKind.Success);
        IsWorkflowDefinitionDraftDirty = false;
        HasWorkflowDefinitionRevisionConflict = false;
        await RefreshWorkflowsSelectingAsync(savedWorkflowDefinition.WorkflowId);
        await LoadSelectedWorkflowDefinitionAsync();
    }
}
