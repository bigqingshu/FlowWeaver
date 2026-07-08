using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string newWorkflowName = "Generated table workflow";

    [ObservableProperty]
    private bool isCreatingWorkflow;

    private bool CanCreateTemplateWorkflow()
    {
        return CanUseEngineActions
            && !IsWorkflowBusy
            && !string.IsNullOrWhiteSpace(NewWorkflowName);
    }

    [RelayCommand(CanExecute = nameof(CanCreateTemplateWorkflow))]
    private async Task CreateTemplateWorkflowAsync()
    {
        var name = NewWorkflowName.Trim();
        if (string.IsNullOrWhiteSpace(name))
        {
            WorkflowMessage = T("workflow.creation_rejected");
            WorkflowErrorMessage = T("workflow.name_required");
            return;
        }

        IsCreatingWorkflow = true;
        WorkflowMessage = F("format.creating_workflow", name);
        WorkflowErrorMessage = null;

        using var definition = TemplateWorkflowDefinitions.CreateGeneratedTable(
            T("workflow.template.generate_rows_display_name"),
            T("workflow.template.keep_amount_gt_one_display_name"));
        var response = await _apiClient.CreateWorkflowAsync(
            BuildSettings(),
            name,
            definition.RootElement,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            WorkflowMessage = F("format.created_workflow", response.Data.Name);
            IsCreatingWorkflow = false;
            await RefreshWorkflowsSelectingAsync(response.Data.WorkflowId);
            return;
        }

        WorkflowMessage = T("workflow.creation_failed");
        WorkflowErrorMessage = DescribeError(response);
        IsCreatingWorkflow = false;
    }
}
