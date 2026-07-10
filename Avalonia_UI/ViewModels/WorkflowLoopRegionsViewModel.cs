using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed partial class WorkflowLoopRegionsViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;
    private readonly Func<string, Task> applyUpdatedDraftAsync;
    private string workflowDefinitionDraftJson = string.Empty;
    private bool isLoading;

    public WorkflowLoopRegionsViewModel(
        Func<string, string> translate,
        Func<string, Task> applyUpdatedDraftAsync)
    {
        this.translate = translate;
        this.applyUpdatedDraftAsync = applyUpdatedDraftAsync;
    }

    public ObservableCollection<WorkflowLoopRegionListItemViewModel> Regions { get; } = new();

    public ObservableCollection<WorkflowLoopRegionNodeOptionViewModel> NodeOptions { get; } = new();

    public ObservableCollection<WorkflowLoopRegionNodeOptionViewModel> EndNodeOptions { get; } = new();

    public ObservableCollection<WorkflowLoopRegionNodeOptionViewModel> BodyNodeOptions { get; } = new();

    [ObservableProperty]
    private WorkflowLoopRegionListItemViewModel? selectedRegion;

    [ObservableProperty]
    private string loopIdDraft = string.Empty;

    [ObservableProperty]
    private WorkflowLoopRegionNodeOptionViewModel? selectedStartNode;

    [ObservableProperty]
    private WorkflowLoopRegionNodeOptionViewModel? selectedJudgeNode;

    [ObservableProperty]
    private WorkflowLoopRegionNodeOptionViewModel? selectedEndNode;

    [ObservableProperty]
    private int maxIterationsDraft = 1;

    [ObservableProperty]
    private bool isEnabledDraft;

    [ObservableProperty]
    private bool isBusy;

    [ObservableProperty]
    private string message = string.Empty;

    [ObservableProperty]
    private string? errorMessage;

    public string SectionText => translate("workflow.loop_regions.section");

    public string AddText => translate("workflow.loop_regions.add");

    public string ApplyText => translate("workflow.loop_regions.apply");

    public string DeleteText => translate("workflow.loop_regions.delete");

    public string DeleteConfirmTitleText => translate("workflow.loop_regions.delete_confirm_title");

    public string DeleteConfirmMessageText => translate("workflow.loop_regions.delete_confirm_message");

    public string LoopIdText => translate("workflow.loop_regions.loop_id");

    public string StartNodeText => translate("workflow.loop_regions.start_node");

    public string JudgeNodeText => translate("workflow.loop_regions.judge_node");

    public string EndNodeText => translate("workflow.loop_regions.end_node");

    public string BodyNodesText => translate("workflow.loop_regions.body_nodes");

    public string MaxIterationsText => translate("workflow.loop_regions.max_iterations");

    public string EnabledText => translate("workflow.loop_regions.enabled");

    public string EmptyText => translate("workflow.loop_regions.empty");

    public string CountText => $"{Regions.Count} {translate("workflow.loop_regions.count_suffix")}";

    public bool HasRegions => Regions.Count > 0;

    public bool HasNoRegions => !HasRegions;

    public bool HasNodes => NodeOptions.Count > 0;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool CanDeleteSelectedRegion => SelectedRegion is not null && !IsBusy;

    public void Load(
        string draftJson,
        WorkflowLoopRegionDraftReadResult readResult,
        IReadOnlyList<WorkflowDefinitionDraftNode> nodes)
    {
        var selectedLoopId = SelectedRegion?.LoopId;
        isLoading = true;
        try
        {
            workflowDefinitionDraftJson = draftJson;
            ReplaceNodeOptions(nodes);
            Regions.Clear();
            if (readResult.Succeeded)
            {
                foreach (var region in readResult.Regions)
                {
                    Regions.Add(new WorkflowLoopRegionListItemViewModel(region, translate));
                }

                ErrorMessage = null;
                Message = Regions.Count == 0 ? EmptyText : string.Empty;
            }
            else
            {
                ErrorMessage = readResult.Warning;
                Message = string.Empty;
            }

            SelectedRegion = Regions.FirstOrDefault(region =>
                string.Equals(region.LoopId, selectedLoopId, StringComparison.Ordinal));
        }
        finally
        {
            isLoading = false;
        }

        if (SelectedRegion is not null)
        {
            LoadEditor(SelectedRegion.Draft);
        }
        else
        {
            ClearEditor();
        }

        NotifyCollectionStateChanged();
    }

    public void RefreshLocalizedText()
    {
        foreach (var region in Regions)
        {
            region.RefreshLocalizedText();
        }

        if (EndNodeOptions.Count > 0 &&
            string.IsNullOrEmpty(EndNodeOptions[0].NodeInstanceId))
        {
            var selectedEndNodeId = SelectedEndNode?.NodeInstanceId;
            EndNodeOptions[0] = new WorkflowLoopRegionNodeOptionViewModel(
                string.Empty,
                translate("workflow.loop_regions.no_end_node"));
            SelectedEndNode = EndNodeOptions.FirstOrDefault(option =>
                string.Equals(option.NodeInstanceId, selectedEndNodeId, StringComparison.Ordinal));
        }

        OnPropertyChanged(nameof(SectionText));
        OnPropertyChanged(nameof(AddText));
        OnPropertyChanged(nameof(ApplyText));
        OnPropertyChanged(nameof(DeleteText));
        OnPropertyChanged(nameof(DeleteConfirmTitleText));
        OnPropertyChanged(nameof(DeleteConfirmMessageText));
        OnPropertyChanged(nameof(LoopIdText));
        OnPropertyChanged(nameof(StartNodeText));
        OnPropertyChanged(nameof(JudgeNodeText));
        OnPropertyChanged(nameof(EndNodeText));
        OnPropertyChanged(nameof(BodyNodesText));
        OnPropertyChanged(nameof(MaxIterationsText));
        OnPropertyChanged(nameof(EnabledText));
        OnPropertyChanged(nameof(EmptyText));
        OnPropertyChanged(nameof(CountText));
    }

    partial void OnSelectedRegionChanged(WorkflowLoopRegionListItemViewModel? value)
    {
        if (!isLoading)
        {
            if (value is null)
            {
                ClearEditor();
            }
            else
            {
                LoadEditor(value.Draft);
            }
        }

        OnPropertyChanged(nameof(CanDeleteSelectedRegion));
        DeleteSelectedRegionCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsBusyChanged(bool value)
    {
        OnPropertyChanged(nameof(CanDeleteSelectedRegion));
        ApplyDraftCommand.NotifyCanExecuteChanged();
        DeleteSelectedRegionCommand.NotifyCanExecuteChanged();
        StartNewDraftCommand.NotifyCanExecuteChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    [RelayCommand(CanExecute = nameof(CanEdit))]
    private void StartNewDraft()
    {
        SelectedRegion = null;
        ClearEditor();
        Message = string.Empty;
        ErrorMessage = null;
    }

    [RelayCommand(CanExecute = nameof(CanEdit))]
    private async Task ApplyDraftAsync()
    {
        var draft = BuildEditorDraft();
        var patchResult = WorkflowLoopRegionDraftPatcher.Upsert(
            workflowDefinitionDraftJson,
            draft,
            SelectedRegion?.LoopId);
        if (!patchResult.Succeeded)
        {
            Message = string.Empty;
            ErrorMessage = patchResult.Warning;
            return;
        }

        IsBusy = true;
        try
        {
            await applyUpdatedDraftAsync(
                patchResult.UpdatedWorkflowDefinitionDraftJson);
            Message = translate("workflow.loop_regions.applied");
            ErrorMessage = null;
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand(CanExecute = nameof(CanDeleteRegion))]
    private async Task DeleteSelectedRegionAsync()
    {
        if (SelectedRegion is null)
        {
            return;
        }

        var patchResult = WorkflowLoopRegionDraftPatcher.Delete(
            workflowDefinitionDraftJson,
            SelectedRegion.LoopId);
        if (!patchResult.Succeeded)
        {
            Message = string.Empty;
            ErrorMessage = patchResult.Warning;
            return;
        }

        IsBusy = true;
        try
        {
            await applyUpdatedDraftAsync(
                patchResult.UpdatedWorkflowDefinitionDraftJson);
            Message = translate("workflow.loop_regions.deleted");
            ErrorMessage = null;
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool CanEdit()
    {
        return !IsBusy && HasNodes && !string.IsNullOrWhiteSpace(workflowDefinitionDraftJson);
    }

    private bool CanDeleteRegion()
    {
        return CanDeleteSelectedRegion;
    }

    private WorkflowLoopRegionDraft BuildEditorDraft()
    {
        var endNodeId = SelectedEndNode?.NodeInstanceId;
        return new WorkflowLoopRegionDraft
        {
            LoopId = LoopIdDraft,
            StartNodeId = SelectedStartNode?.NodeInstanceId ?? string.Empty,
            JudgeNodeId = SelectedJudgeNode?.NodeInstanceId ?? string.Empty,
            BodyNodeIds = BodyNodeOptions
                .Where(option => option.IsBodySelected)
                .Select(option => option.NodeInstanceId)
                .ToArray(),
            EndNodeId = string.IsNullOrWhiteSpace(endNodeId)
                ? null
                : endNodeId,
            MaxIterations = MaxIterationsDraft,
            Enabled = IsEnabledDraft,
        };
    }

    private void ReplaceNodeOptions(IReadOnlyList<WorkflowDefinitionDraftNode> nodes)
    {
        NodeOptions.Clear();
        EndNodeOptions.Clear();
        BodyNodeOptions.Clear();
        EndNodeOptions.Add(new WorkflowLoopRegionNodeOptionViewModel(
            string.Empty,
            translate("workflow.loop_regions.no_end_node")));
        foreach (var node in nodes)
        {
            var displayText = string.IsNullOrWhiteSpace(node.DisplayName)
                ? $"{node.NodeInstanceId} ({node.NodeTypeDisplayName})"
                : $"{node.DisplayName} [{node.NodeInstanceId}]";
            NodeOptions.Add(new WorkflowLoopRegionNodeOptionViewModel(
                node.NodeInstanceId,
                displayText));
            EndNodeOptions.Add(new WorkflowLoopRegionNodeOptionViewModel(
                node.NodeInstanceId,
                displayText));
            BodyNodeOptions.Add(new WorkflowLoopRegionNodeOptionViewModel(
                node.NodeInstanceId,
                displayText));
        }
    }

    private void LoadEditor(WorkflowLoopRegionDraft draft)
    {
        LoopIdDraft = draft.LoopId;
        SelectedStartNode = FindOption(NodeOptions, draft.StartNodeId);
        SelectedJudgeNode = FindOption(NodeOptions, draft.JudgeNodeId);
        SelectedEndNode = FindOption(EndNodeOptions, draft.EndNodeId ?? string.Empty);
        MaxIterationsDraft = draft.MaxIterations;
        IsEnabledDraft = draft.Enabled;
        var bodyNodeIds = draft.BodyNodeIds.ToHashSet(StringComparer.Ordinal);
        foreach (var option in BodyNodeOptions)
        {
            option.IsBodySelected = bodyNodeIds.Contains(option.NodeInstanceId);
        }
    }

    private void ClearEditor()
    {
        LoopIdDraft = string.Empty;
        SelectedStartNode = NodeOptions.FirstOrDefault();
        SelectedJudgeNode = NodeOptions.Skip(1).FirstOrDefault() ?? NodeOptions.FirstOrDefault();
        SelectedEndNode = EndNodeOptions.FirstOrDefault();
        MaxIterationsDraft = 1;
        IsEnabledDraft = false;
        foreach (var option in BodyNodeOptions)
        {
            option.IsBodySelected = false;
        }
    }

    private static WorkflowLoopRegionNodeOptionViewModel? FindOption(
        IEnumerable<WorkflowLoopRegionNodeOptionViewModel> options,
        string nodeInstanceId)
    {
        return options.FirstOrDefault(option =>
            string.Equals(option.NodeInstanceId, nodeInstanceId, StringComparison.Ordinal));
    }

    private void NotifyCollectionStateChanged()
    {
        OnPropertyChanged(nameof(HasRegions));
        OnPropertyChanged(nameof(HasNoRegions));
        OnPropertyChanged(nameof(HasNodes));
        OnPropertyChanged(nameof(CountText));
        ApplyDraftCommand.NotifyCanExecuteChanged();
        StartNewDraftCommand.NotifyCanExecuteChanged();
    }
}
