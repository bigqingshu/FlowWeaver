using System;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowLoopRegionListItemViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;

    public WorkflowLoopRegionListItemViewModel(
        WorkflowLoopRegionDraft draft,
        Func<string, string> translate)
    {
        Draft = draft;
        this.translate = translate;
    }

    public WorkflowLoopRegionDraft Draft { get; }

    public string LoopId => Draft.LoopId;

    public string BoundaryText => $"{Draft.StartNodeId} -> {Draft.JudgeNodeId}";

    public string IterationText => $"{translate("workflow.loop_regions.max_iterations")}: {Draft.MaxIterations}";

    public string EnabledText => translate(
        Draft.Enabled ? "common.on" : "common.off");

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(IterationText));
        OnPropertyChanged(nameof(EnabledText));
    }
}

public sealed partial class WorkflowLoopRegionNodeOptionViewModel : ViewModelBase
{
    public WorkflowLoopRegionNodeOptionViewModel(
        string nodeInstanceId,
        string displayText)
    {
        NodeInstanceId = nodeInstanceId;
        DisplayText = displayText;
    }

    public string NodeInstanceId { get; }

    public string DisplayText { get; }

    [ObservableProperty]
    private bool isBodySelected;
}
