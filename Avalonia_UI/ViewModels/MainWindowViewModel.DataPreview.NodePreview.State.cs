using System.Collections.ObjectModel;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int dataPreviewLoadVersion;

    [ObservableProperty]
    private bool isLoadingDataPreview;

    [ObservableProperty]
    private string dataPreviewMessage =
        "Select a run and workflow node to load data preview.";

    [ObservableProperty]
    private string? dataPreviewErrorMessage;

    private string? dataPreviewSourceWorkflowRunId;

    private string? dataPreviewSourceNodeInstanceId;

    private string? dataPreviewSourceLogicalTableId;

    private string? dataPreviewSourceTableRefId;

    private string? dataPreviewSourceRunMode;

    private string? dataPreviewSourceTargetNodeInstanceId;

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewRows { get; } =
        new();

}
