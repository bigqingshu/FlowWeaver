using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanValidateWorkflowDefinitionDraft))]
    private async Task ValidateWorkflowDefinitionDraftAsync()
    {
        if (!FlushPendingNodeConfigAutoSave())
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(WorkflowDefinitionDraftJson))
        {
            RejectWorkflowDefinitionDraftValidationWithoutDraft();
            return;
        }

        if (!TryReadWorkflowDefinitionDraftJsonForValidation(out var definition))
        {
            return;
        }

        BeginWorkflowDefinitionDraftValidation();

        var response = await _apiClient.ValidateWorkflowDraftAsync(
            BuildSettings(),
            definition,
            _shutdown.Token);

        if (response.Ok && response.Data is not null)
        {
            ApplyWorkflowDefinitionDraftValidationSuccess(response.Data);
            return;
        }

        ApplyWorkflowDefinitionDraftValidationFailure(response);
    }
}
