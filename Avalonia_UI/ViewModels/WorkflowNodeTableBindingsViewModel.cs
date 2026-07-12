using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed partial class WorkflowNodeTableBindingsViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;
    private readonly Func<string, Task> applyUpdatedDraftAsync;
    private readonly NodeTableBindingCandidateBuilder candidateBuilder = new();
    private string workflowDefinitionDraftJson = string.Empty;
    private string currentNodeInstanceId = string.Empty;
    private bool isLoading;
    private bool isSynchronizingOutput;
    private bool outputManuallyEdited;

    public WorkflowNodeTableBindingsViewModel(
        Func<string, string> translate,
        Func<string, Task> applyUpdatedDraftAsync)
    {
        this.translate = translate;
        this.applyUpdatedDraftAsync = applyUpdatedDraftAsync;
    }

    public ObservableCollection<NodeTableInputBindingViewModel> InputBindings { get; } = new();

    public ObservableCollection<NodeTableOutputTargetViewModel> OutputTargets { get; } = new();

    [ObservableProperty]
    private bool isBusy;

    [ObservableProperty]
    private string message = string.Empty;

    [ObservableProperty]
    private string? errorMessage;

    public string InputSectionText => translate("workflow.table_bindings.inputs");

    public string OutputSectionText => translate("workflow.table_bindings.outputs");

    public string ApplyText => translate("workflow.table_bindings.apply");

    public bool HasInputSlots => InputBindings.Count > 0;

    public bool HasOutputSlots => OutputTargets.Count > 0;

    public bool HasSlots => HasInputSlots || HasOutputSlots;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public void Load(
        string draftJson,
        string draftRevision,
        WorkflowDefinitionDraftSnapshot snapshot,
        string selectedNodeInstanceId,
        NodeDefinitionDto? selectedDefinition,
        IReadOnlyCollection<NodeDefinitionDto> nodeDefinitions,
        string catalogHash,
        IReadOnlyCollection<RunTableDirectoryItemDto> tableCatalog,
        NodeTableBindingsDraftReadResult readResult)
    {
        isLoading = true;
        try
        {
            workflowDefinitionDraftJson = draftJson;
            currentNodeInstanceId = selectedNodeInstanceId;
            InputBindings.Clear();
            OutputTargets.Clear();
            outputManuallyEdited = false;
            Message = string.Empty;
            ErrorMessage = readResult.Succeeded ? null : readResult.Warning;
            if (selectedDefinition is null || !readResult.Succeeded)
            {
                return;
            }

            var candidates = candidateBuilder.Build(
                snapshot,
                draftRevision,
                selectedNodeInstanceId,
                catalogHash,
                nodeDefinitions,
                tableCatalog);
            var existingTargets = MergeStableExistingTargets(candidates);
            foreach (var slot in selectedDefinition.InputTableSlots)
            {
                InputBindings.Add(new NodeTableInputBindingViewModel(
                    slot,
                    candidates.InputCandidates,
                    readResult.InputBindings.FirstOrDefault(binding =>
                        binding.Slot == slot.Name),
                    translate,
                    OnInputSelectionChanged));
            }

            foreach (var slot in selectedDefinition.OutputTableSlots)
            {
                OutputTargets.Add(new NodeTableOutputTargetViewModel(
                    slot,
                    existingTargets,
                    readResult.OutputTargets.FirstOrDefault(target =>
                        target.Slot == slot.Name),
                    translate,
                    OnOutputTargetChanged));
            }
        }
        finally
        {
            isLoading = false;
            NotifyStateChanged();
        }
    }

    public void Clear()
    {
        isLoading = true;
        try
        {
            workflowDefinitionDraftJson = string.Empty;
            currentNodeInstanceId = string.Empty;
            InputBindings.Clear();
            OutputTargets.Clear();
            Message = string.Empty;
            ErrorMessage = null;
            outputManuallyEdited = false;
        }
        finally
        {
            isLoading = false;
            NotifyStateChanged();
        }
    }

    partial void OnIsBusyChanged(bool value)
    {
        ApplyBindingsCommand.NotifyCanExecuteChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
        ApplyBindingsCommand.NotifyCanExecuteChanged();
    }

    [RelayCommand(CanExecute = nameof(CanApplyBindings))]
    private async Task ApplyBindingsAsync()
    {
        var inputs = InputBindings
            .Select(binding => binding.BuildDraft())
            .Where(binding => binding is not null)
            .Cast<NodeTableInputBindingDraft>()
            .ToArray();
        var outputs = OutputTargets
            .Select(target => target.BuildDraft())
            .Where(target => target is not null)
            .Cast<NodeTableOutputTargetDraft>()
            .ToArray();
        var patchResult = NodeTableBindingsDraftPatcher.Apply(
            workflowDefinitionDraftJson,
            currentNodeInstanceId,
            inputs,
            outputs);
        if (!patchResult.Succeeded)
        {
            Message = string.Empty;
            ErrorMessage = patchResult.Warning;
            return;
        }

        IsBusy = true;
        try
        {
            await applyUpdatedDraftAsync(patchResult.UpdatedWorkflowDefinitionDraftJson);
            Message = translate("workflow.table_bindings.applied");
            ErrorMessage = null;
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool CanApplyBindings()
    {
        return !IsBusy &&
            HasSlots &&
            !HasError &&
            !string.IsNullOrWhiteSpace(workflowDefinitionDraftJson) &&
            !string.IsNullOrWhiteSpace(currentNodeInstanceId) &&
            InputBindings.All(binding => !binding.IsRequired || binding.HasSelection) &&
            OutputTargets.All(target => target.IsValid);
    }

    private void OnInputSelectionChanged(NodeTableInputBindingViewModel input)
    {
        if (isLoading)
        {
            return;
        }

        if (!outputManuallyEdited)
        {
            var output = OutputTargets.FirstOrDefault(target => target.SlotName == input.SlotName)
                ?? OutputTargets.FirstOrDefault();
            var draft = input.BuildDraft();
            if (draft is not null && output is not null)
            {
                isSynchronizingOutput = true;
                try
                {
                    output.TryApplyInputSuggestion(draft);
                }
                finally
                {
                    isSynchronizingOutput = false;
                }
            }
        }

        ApplyBindingsCommand.NotifyCanExecuteChanged();
    }

    private void OnOutputTargetChanged()
    {
        if (!isLoading && !isSynchronizingOutput)
        {
            outputManuallyEdited = true;
        }

        ApplyBindingsCommand.NotifyCanExecuteChanged();
    }

    private static IReadOnlyList<NodeTableExistingOutputTargetCandidate>
        MergeStableExistingTargets(NodeTableBindingCandidateSet candidates)
    {
        var fromInputs = candidates.InputCandidates
            .Where(candidate =>
                candidate.OutputRole == "AUXILIARY" &&
                candidate.StorageKind is "MEMORY" or "RUNTIME_SQL" &&
                !string.IsNullOrWhiteSpace(candidate.LogicalTableId))
            .Select(candidate => new NodeTableExistingOutputTargetCandidate
            {
                StorageKind = candidate.StorageKind!,
                Role = "AUXILIARY",
                LogicalTableId = candidate.LogicalTableId!,
                LatestTableRefId = candidate.RecentTableRefId,
                Version = candidate.RecentVersion ?? 0,
                LifecycleStatus = candidate.RecentLifecycleStatus ?? string.Empty,
            });
        return candidates.ExistingOutputTargets
            .Concat(fromInputs)
            .GroupBy(candidate => (
                candidate.StorageKind,
                candidate.Role,
                candidate.LogicalTableId))
            .Select(group => group
                .OrderByDescending(candidate => candidate.Version)
                .First())
            .ToArray();
    }

    private void NotifyStateChanged()
    {
        OnPropertyChanged(nameof(InputSectionText));
        OnPropertyChanged(nameof(OutputSectionText));
        OnPropertyChanged(nameof(ApplyText));
        OnPropertyChanged(nameof(HasInputSlots));
        OnPropertyChanged(nameof(HasOutputSlots));
        OnPropertyChanged(nameof(HasSlots));
        OnPropertyChanged(nameof(HasError));
        ApplyBindingsCommand.NotifyCanExecuteChanged();
    }
}
