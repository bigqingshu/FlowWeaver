using System.Collections.ObjectModel;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string currentLanguageCode = SupportedLanguage.Default.Code;

    [ObservableProperty]
    private string currentThemeVariant = PersistedUiSettings.SystemThemeVariant;

    public ObservableCollection<LanguageMenuItemViewModel> Languages { get; } = new();

    public ObservableCollection<ThemeMenuItemViewModel> Themes { get; } = new();

    public string AppTitleText => T("app.title");

    public string AppSubtitleText => T("app.subtitle");

    public string SettingsMenuText => T("settings.menu");

    public string LanguageMenuText => T("settings.language");

    public string LanguageMenuHeaderText => $"{LanguageMenuText}: {T($"language.{CurrentLanguageCode}")}";

    public string ThemeMenuText => T("settings.theme");

    public string ThemeMenuHeaderText => $"{ThemeMenuText}: {T($"theme.{CurrentThemeVariant.ToLowerInvariant()}")}";

    public string LightThemeText => T("theme.light");

    public string DarkThemeText => T("theme.dark");

    public string SystemThemeText => T("theme.system");

    public string EnglishLanguageText => T("language.en-US");

    public string SimplifiedChineseLanguageText => T("language.zh-Hans");

    [RelayCommand]
    private async Task ChangeLanguageAsync(string? languageCode)
    {
        await ApplyLanguageAsync(
            languageCode ?? SupportedLanguage.Default.Code,
            save: true,
            _shutdown.Token);
    }

    [RelayCommand]
    private async Task ChangeThemeAsync(string? themeVariantStr)
    {
        await ApplyThemeAsync(
            themeVariantStr ?? PersistedUiSettings.SystemThemeVariant,
            save: true,
            _shutdown.Token);
    }

    private async Task ApplyLanguageAsync(
        string languageCode,
        bool save,
        CancellationToken cancellationToken)
    {
        var previousDefaults = CaptureDefaultMessageSnapshot();
        await _localizationService.SetLanguageAsync(languageCode, cancellationToken);
        CurrentLanguageCode = _localizationService.CurrentLanguageCode;
        foreach (var language in Languages)
        {
            language.IsSelected = language.Code == CurrentLanguageCode;
        }

        NotifyLocalizedTextChanged();
        RefreshDefaultMessagesForCurrentLanguage(previousDefaults);
        if (save)
        {
            await _uiSettingsStore.SaveAsync(
                PersistedUiSettings.FromSettings(CurrentLanguageCode, CurrentThemeVariant),
                cancellationToken);
        }
    }

    private async Task ApplyThemeAsync(
        string themeVariant,
        bool save,
        CancellationToken cancellationToken)
    {
        CurrentThemeVariant = PersistedUiSettings.NormalizeThemeVariantOrDefault(themeVariant);
        foreach (var theme in Themes)
        {
            theme.IsSelected = theme.ThemeVariant == CurrentThemeVariant;
        }

        if (Avalonia.Application.Current != null)
        {
            Avalonia.Application.Current.RequestedThemeVariant = CurrentThemeVariant switch
            {
                PersistedUiSettings.LightThemeVariant => Avalonia.Styling.ThemeVariant.Light,
                PersistedUiSettings.DarkThemeVariant => Avalonia.Styling.ThemeVariant.Dark,
                _ => Avalonia.Styling.ThemeVariant.Default
            };
        }

        OnPropertyChanged(nameof(ThemeMenuHeaderText));

        if (save)
        {
            await _uiSettingsStore.SaveAsync(
                PersistedUiSettings.FromSettings(CurrentLanguageCode, CurrentThemeVariant),
                cancellationToken);
        }
    }

    private string T(string key)
    {
        return _localizationService.GetString(key);
    }

    private string F(string key, params object?[] args)
    {
        return _localizationService.Format(key, args);
    }

    private void NotifyLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(AppTitleText));
        OnPropertyChanged(nameof(AppSubtitleText));
        OnPropertyChanged(nameof(SettingsMenuText));
        OnPropertyChanged(nameof(LanguageMenuText));
        OnPropertyChanged(nameof(LanguageMenuHeaderText));
        OnPropertyChanged(nameof(ThemeMenuText));
        OnPropertyChanged(nameof(ThemeMenuHeaderText));
        OnPropertyChanged(nameof(LightThemeText));
        OnPropertyChanged(nameof(DarkThemeText));
        OnPropertyChanged(nameof(SystemThemeText));
        OnPropertyChanged(nameof(EnglishLanguageText));
        OnPropertyChanged(nameof(SimplifiedChineseLanguageText));
        OnPropertyChanged(nameof(ConnectionBaseUrlText));
        OnPropertyChanged(nameof(ConnectionTokenText));
        OnPropertyChanged(nameof(ConnectionStatusText));
        OnPropertyChanged(nameof(ConnectionEventsText));
        OnPropertyChanged(nameof(CheckConnectionText));
        OnPropertyChanged(nameof(StreamText));
        OnPropertyChanged(nameof(StopText));
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
        OnPropertyChanged(nameof(ExecutionTabText));
        OnPropertyChanged(nameof(DefinitionTabText));
        OnPropertyChanged(nameof(LogsTabText));
        OnPropertyChanged(nameof(DataTabText));
        OnPropertyChanged(nameof(DataPreviewTabText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPendingText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(DataPreviewTableSelectorText));
        OnPropertyChanged(nameof(DataPreviewStateSelectorText));
        OnPropertyChanged(nameof(DataPreviewLoadSelectedTableText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchRefreshText));
        OnPropertyChanged(nameof(DataPreviewDetailsText));
        OnPropertyChanged(nameof(DataPreviewSearchText));
        OnPropertyChanged(nameof(DataPreviewSearchWatermarkText));
        OnPropertyChanged(nameof(DataPreviewCopyTsvText));
        OnPropertyChanged(nameof(DataPreviewPasteText));
        OnPropertyChanged(nameof(DataPreviewPasteWatermarkText));
        OnPropertyChanged(nameof(DataPreviewParsePasteText));
        OnPropertyChanged(nameof(DataPreviewRestoreDraftText));
        OnPropertyChanged(nameof(DataPreviewSaveAsText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchDirtyStateText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        OnPropertyChanged(nameof(DataPreviewPreviousPageText));
        OnPropertyChanged(nameof(DataPreviewNextPageText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        OnPropertyChanged(nameof(WorkflowsSectionText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(CloseText));
        OnPropertyChanged(nameof(RunText));
        OnPropertyChanged(nameof(WorkflowRunGuardText));
        OnPropertyChanged(nameof(CreateText));
        OnPropertyChanged(nameof(ImportWorkflowText));
        OnPropertyChanged(nameof(ExportWorkflowText));
        OnPropertyChanged(nameof(DeleteWorkflowText));
        OnPropertyChanged(nameof(DeleteWorkflowConfirmTitleText));
        OnPropertyChanged(nameof(DeleteWorkflowConfirmMessageText));
        OnPropertyChanged(nameof(CanUseImportWorkflowAction));
        OnPropertyChanged(nameof(ImportWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseExportSelectedWorkflowAction));
        OnPropertyChanged(nameof(ExportSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(WorkflowNameWatermarkText));
        OnPropertyChanged(nameof(RunsSectionText));
        OnPropertyChanged(nameof(CancelText));
        OnPropertyChanged(nameof(CancelConfirmTitleText));
        OnPropertyChanged(nameof(CancelConfirmMessageText));
        OnPropertyChanged(nameof(NodeRunsSectionText));
        OnPropertyChanged(nameof(WorkflowDefinitionSectionText));
        OnPropertyChanged(nameof(DetailsText));
        OnPropertyChanged(nameof(NameLabelText));
        OnPropertyChanged(nameof(VersionLabelText));
        OnPropertyChanged(nameof(RevisionLabelText));
        OnPropertyChanged(nameof(StatusLabelText));
        OnPropertyChanged(nameof(HashLabelText));
        OnPropertyChanged(nameof(UpdatedLabelText));
        OnPropertyChanged(nameof(NodesSectionText));
        OnPropertyChanged(nameof(WorkflowNodesSectionText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(NodeConfigSectionText));
        OnPropertyChanged(nameof(ApplyNodeConfigText));
        OnPropertyChanged(nameof(ApplyNodeDisplayNameText));
        OnPropertyChanged(nameof(RuntimeOptionsSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsOpenEditorText));
        OnPropertyChanged(nameof(RuntimeOptionsWindowTitleText));
        OnPropertyChanged(nameof(RuntimeOptionsWorkflowSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsNodeOverrideSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsProfileText));
        OnPropertyChanged(nameof(RuntimeOptionsProfileOptions));
        OnPropertyChanged(nameof(RuntimeOptionsStrictValidationText));
        OnPropertyChanged(nameof(RuntimeOptionsLogLevelText));
        OnPropertyChanged(nameof(RuntimeOptionsLogLevelOptions));
        OnPropertyChanged(nameof(RuntimeOptionsEventLevelText));
        OnPropertyChanged(nameof(RuntimeOptionsEventLevelOptions));
        OnPropertyChanged(nameof(RuntimeOptionsEventRateLimitText));
        OnPropertyChanged(nameof(RuntimeOptionsProgressEnabledText));
        OnPropertyChanged(nameof(RuntimeOptionsProgressIntervalText));
        OnPropertyChanged(nameof(RuntimeOptionsCaptureErrorContextText));
        OnPropertyChanged(nameof(RuntimeOptionsIncludeMetricsText));
        OnPropertyChanged(nameof(RuntimeOptionsPayloadByteLimitText));
        OnPropertyChanged(nameof(RuntimeOptionsTtlSecondsText));
        OnPropertyChanged(nameof(RuntimeOptionsRedactColumnsText));
        OnPropertyChanged(nameof(RuntimeOptionsMaskPolicyText));
        OnPropertyChanged(nameof(RuntimeOptionsMaskPolicyOptions));
        OnPropertyChanged(nameof(RuntimeOptionsJsonSectionText));
        OnPropertyChanged(nameof(RuntimeOptionsJsonRegenerateText));
        OnPropertyChanged(nameof(RuntimeOptionsJsonWatermarkText));
        OnPropertyChanged(nameof(RuntimeOptionsSelectNodeText));
        OnPropertyChanged(nameof(RuntimeOptionsApplyText));
        OnPropertyChanged(nameof(RuntimeOptionsResetNodeOverrideText));
        NotifyRuntimeOptionsSummaryChanged();
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
        OnPropertyChanged(nameof(StructuredEditSectionText));
        OnPropertyChanged(nameof(AddNodeText));
        OnPropertyChanged(nameof(CopyNodeText));
        OnPropertyChanged(nameof(DeleteNodeText));
        OnPropertyChanged(nameof(DeleteSelectedNodesText));
        OnPropertyChanged(nameof(MoveNodeUpText));
        OnPropertyChanged(nameof(MoveNodeDownText));
        OnPropertyChanged(nameof(NodeActionsSectionText));
        OnPropertyChanged(nameof(NodeMoveSemanticsText));
        OnPropertyChanged(nameof(WorkflowLinearChainStatusText));
        NotifyWorkflowDefinitionNodeActionDisabledReasonsChanged();
        OnPropertyChanged(nameof(DataPreviewSectionText));
        OnPropertyChanged(nameof(DataPreviewEmptyText));
        OnPropertyChanged(nameof(DataPreviewPendingText));
        OnPropertyChanged(nameof(DataPreviewRefreshText));
        OnPropertyChanged(nameof(PreviewSelectedNodeText));
        OnPropertyChanged(nameof(DataPreviewSourceText));
        OnPropertyChanged(nameof(RestoreText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
        OnPropertyChanged(nameof(NodeInstanceIdText));
        OnPropertyChanged(nameof(NodeTypeText));
        OnPropertyChanged(nameof(NodeVersionText));
        OnPropertyChanged(nameof(DisplayNameText));
        OnPropertyChanged(nameof(ConfigJsonText));
        OnPropertyChanged(nameof(ConnectionsSectionText));
        OnPropertyChanged(nameof(ShowConnectionsText));
        OnPropertyChanged(nameof(AddConnectionText));
        OnPropertyChanged(nameof(DeleteConnectionText));
        OnPropertyChanged(nameof(ConnectionIdText));
        OnPropertyChanged(nameof(SourceNodeText));
        OnPropertyChanged(nameof(SourcePortText));
        OnPropertyChanged(nameof(TargetNodeText));
        OnPropertyChanged(nameof(TargetPortText));
        OnPropertyChanged(nameof(RecentEventsSectionText));
        OnPropertyChanged(nameof(RecentEventsEmptyText));
        OnPropertyChanged(nameof(RecentEventsViewAllText));
        OnPropertyChanged(nameof(RecentEventsToggleText));
        OnPropertyChanged(nameof(NodeCatalogSectionText));
        OnPropertyChanged(nameof(NodeText));
        OnPropertyChanged(nameof(NodeCatalogEmptyStateText));
        OnPropertyChanged(nameof(InputsText));
        OnPropertyChanged(nameof(OutputsText));
        OnPropertyChanged(nameof(ModeText));
        OnPropertyChanged(nameof(TimeoutText));
        OnPropertyChanged(nameof(DraftJsonSectionText));
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
        OnPropertyChanged(nameof(WorkflowRunFilterText));
        OnPropertyChanged(nameof(RunIdWatermarkText));
        OnPropertyChanged(nameof(NodeRunFilterText));
        OnPropertyChanged(nameof(NodeRunIdWatermarkText));
        OnPropertyChanged(nameof(EventTypeFilterText));
        OnPropertyChanged(nameof(AfterFilterText));
        OnPropertyChanged(nameof(SequenceWatermarkText));
        OnPropertyChanged(nameof(RuntimeText));
        OnPropertyChanged(nameof(LimitText));
        OnPropertyChanged(nameof(RuntimeEventsSectionText));
        OnPropertyChanged(nameof(TableRefsSectionText));
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
        foreach (var nodeDefinition in NodeDefinitions)
        {
            nodeDefinition.RefreshLocalizedText();
        }

        RefreshShellNavigationItems();
        InvalidateWorkflowDefinitionDraftParseCache();
        RefreshWorkflowDefinitionDraftStructureState();
        RefreshSelectedNodeConfigDraftState();
    }
}
