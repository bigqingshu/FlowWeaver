using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class ReadSharedTablesNodeEditorViewModel : ViewModelBase,
    INodeSpecializedEditorViewModel
{
    private const int SharePageSize = 50;
    private const int VersionPageSize = 50;
    private const int MemberPageSize = 100;

    private readonly ISharedPublicationCatalogService _catalogService;
    private readonly ILocalizationService _localizationService;
    private readonly CancellationToken _lifetimeToken;
    private readonly List<string> _selectedMemberNames;
    private CancellationTokenSource? _shareRequestCts;
    private CancellationTokenSource? _versionRequestCts;
    private CancellationTokenSource? _memberRequestCts;
    private int _shareRequestVersion;
    private int _versionRequestVersion;
    private int _memberRequestVersion;
    private int _shareOffset;
    private int _versionOffset;
    private int _memberOffset;
    private bool _versionsFullyLoaded;
    private bool _membersFullyLoaded;
    private bool _versionDirectoryLoaded;
    private bool _memberDirectoryLoaded;
    private bool _suppressConfigChanged;
    private string? _directoryShareName;
    private string? _selectedPublicationId;
    private bool _disposed;

    private ReadSharedTablesNodeEditorViewModel(
        NodeSpecializedEditorContext context,
        NodeConfigEditableFieldInputViewModel shareNameField,
        NodeConfigEditableFieldInputViewModel versionPolicyField,
        NodeConfigEditableFieldInputViewModel? exactVersionField,
        NodeConfigEditableFieldInputViewModel? selectedMembersField)
    {
        NodeType = context.Node.NodeType;
        ShareNameField = shareNameField;
        VersionPolicyField = versionPolicyField;
        ExactVersionField = exactVersionField;
        SelectedMembersField = selectedMembersField;
        _catalogService = context.CatalogService;
        _localizationService = context.LocalizationService;
        _lifetimeToken = context.LifetimeToken;
        shareName = shareNameField.InputValue;
        _directoryShareName = shareNameField.InputValue.Trim();
        shareSearchText = shareNameField.InputValue;
        exactVersionText = exactVersionField?.InputValue ?? string.Empty;
        isExactVersionPolicy = string.Equals(
            versionPolicyField.InputValue,
            "EXACT_VERSION",
            StringComparison.Ordinal);
        isLatestVersionPolicy = !isExactVersionPolicy;
        _selectedMemberNames = selectedMembersField?.StringArrayItems
            .Select(item => item.Value)
            .Distinct(StringComparer.Ordinal)
            .ToList() ?? [];
    }

    public static ReadSharedTablesNodeEditorViewModel? TryCreate(
        NodeSpecializedEditorContext context)
    {
        var shareNameField = FindField(context.Fields, "share_name");
        var versionPolicyField = FindField(context.Fields, "version_policy");
        var selectedMembersField = FindField(context.Fields, "selected_members");
        var exactVersionField = FindField(context.Fields, "exact_version");
        if (shareNameField is null
            || versionPolicyField is null
            || exactVersionField is null
            || selectedMembersField?.IsStringArrayInput != true)
        {
            return null;
        }

        return new ReadSharedTablesNodeEditorViewModel(
            context,
            shareNameField,
            versionPolicyField,
            exactVersionField,
            selectedMembersField);
    }

    public string NodeType { get; }

    public event EventHandler? ConfigChanged;

    public NodeConfigEditableFieldInputViewModel ShareNameField { get; }

    public NodeConfigEditableFieldInputViewModel VersionPolicyField { get; }

    public NodeConfigEditableFieldInputViewModel? ExactVersionField { get; }

    public NodeConfigEditableFieldInputViewModel? SelectedMembersField { get; }

    public ObservableCollection<SharedPublicationShareOptionViewModel> ShareOptions { get; } =
        new();

    public ObservableCollection<SharedPublicationVersionOptionViewModel> VersionOptions { get; } =
        new();

    public ObservableCollection<SharedPublicationMemberOptionViewModel> MemberOptions { get; } =
        new();

    [ObservableProperty]
    private string shareSearchText = string.Empty;

    [ObservableProperty]
    private string shareName = string.Empty;

    [ObservableProperty]
    private string exactVersionText = string.Empty;

    [ObservableProperty]
    private bool isLatestVersionPolicy;

    [ObservableProperty]
    private bool isExactVersionPolicy;

    [ObservableProperty]
    private SharedPublicationShareOptionViewModel? selectedShareOption;

    [ObservableProperty]
    private SharedPublicationVersionOptionViewModel? selectedVersionOption;

    [ObservableProperty]
    private bool isLoadingShares;

    [ObservableProperty]
    private bool isLoadingVersions;

    [ObservableProperty]
    private bool isLoadingMembers;

    [ObservableProperty]
    private bool hasMoreShares;

    [ObservableProperty]
    private bool hasMoreVersions;

    [ObservableProperty]
    private bool hasMoreMembers;

    [ObservableProperty]
    private string? errorMessage;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public string ShareSearchTextLabel =>
        _localizationService.GetString("node_config.shared.read.search_shares");

    public string ShareNameText =>
        _localizationService.GetString("node_config.shared.share_name");

    public string VersionPolicyText =>
        _localizationService.GetString("node_config.shared.read.version_policy");

    public string LatestText =>
        _localizationService.GetString("node_config.shared.read.latest");

    public string ExactVersionTextLabel =>
        _localizationService.GetString("node_config.shared.read.exact_version");

    public string MembersText =>
        _localizationService.GetString("node_config.shared.read.members");

    public string SearchText =>
        _localizationService.GetString("node_config.shared.read.search");

    public string RefreshText =>
        _localizationService.GetString("common.refresh");

    public string LoadMoreText =>
        _localizationService.GetString("node_config.shared.read.load_more");

    public string ClearMembersText =>
        _localizationService.GetString("node_config.shared.read.clear_members");

    [RelayCommand(AllowConcurrentExecutions = true)]
    private Task RefreshSharesAsync()
    {
        return LoadSharesAsync(reset: true);
    }

    private bool CanLoadMoreShares()
    {
        return HasMoreShares && !IsLoadingShares;
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreShares))]
    private Task LoadMoreSharesAsync()
    {
        return LoadSharesAsync(reset: false);
    }

    [RelayCommand(AllowConcurrentExecutions = true)]
    private Task RefreshVersionsAsync()
    {
        return LoadVersionsAsync(reset: true);
    }

    private bool CanLoadMoreVersions()
    {
        return HasMoreVersions && !IsLoadingVersions;
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreVersions))]
    private Task LoadMoreVersionsAsync()
    {
        return LoadVersionsAsync(reset: false);
    }

    private bool CanLoadMoreMembers()
    {
        return HasMoreMembers
            && !IsLoadingMembers
            && SelectedVersionOption is not null;
    }

    [RelayCommand(CanExecute = nameof(CanLoadMoreMembers))]
    private Task LoadMoreMembersAsync()
    {
        return LoadMembersAsync(reset: false);
    }

    [RelayCommand]
    private void UseLatestVersion()
    {
        SetVersionPolicy(exact: false);
    }

    [RelayCommand]
    private void UseExactVersion()
    {
        SetVersionPolicy(exact: true);
    }

    [RelayCommand]
    private void ClearSelectedMembers()
    {
        var changed = _selectedMemberNames.Count > 0;
        _suppressConfigChanged = true;
        _selectedMemberNames.Clear();
        try
        {
            foreach (var member in MemberOptions)
            {
                member.IsSelected = false;
            }
        }
        finally
        {
            _suppressConfigChanged = false;
        }

        if (changed)
        {
            ConfigChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    public bool TryPrepareApply(out string errorMessage)
    {
        var normalizedShareName = ShareName?.Trim() ?? string.Empty;
        if (normalizedShareName.Length == 0)
        {
            errorMessage = _localizationService.GetString(
                "node_config.shared.error.share_name_required");
            return false;
        }

        if (IsExactVersionPolicy)
        {
            if (!int.TryParse(
                ExactVersionText,
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out var exactVersion)
                || exactVersion <= 0)
            {
                errorMessage = _localizationService.GetString(
                    "node_config.shared.error.exact_version_positive");
                return false;
            }

            var matchingVersion = VersionOptions.FirstOrDefault(
                option => option.PublicationVersion == exactVersion);
            if (_versionDirectoryLoaded && matchingVersion is null)
            {
                errorMessage = _localizationService.GetString(
                    _versionsFullyLoaded
                        ? "node_config.shared.error.version_missing"
                        : "node_config.shared.error.version_not_loaded");
                return false;
            }

            if (matchingVersion is not null && !matchingVersion.IsPublished)
            {
                errorMessage = _localizationService.GetString(
                    "node_config.shared.error.version_unavailable");
                return false;
            }
        }

        if (_memberDirectoryLoaded)
        {
            var availableNames = MemberOptions
                .Select(member => member.ExportName)
                .ToHashSet(StringComparer.Ordinal);
            if (_selectedMemberNames.Any(name => !availableNames.Contains(name)))
            {
                errorMessage = _localizationService.GetString(
                    _membersFullyLoaded
                        ? "node_config.shared.error.member_missing"
                        : "node_config.shared.error.member_not_loaded");
                return false;
            }
        }

        ShareName = normalizedShareName;
        ShareNameField.InputValue = normalizedShareName;
        ShareNameField.HasInputValue = true;
        VersionPolicyField.InputValue = IsExactVersionPolicy
            ? "EXACT_VERSION"
            : "LATEST";
        VersionPolicyField.HasInputValue = true;
        if (ExactVersionField is not null)
        {
            ExactVersionField.InputValue = ExactVersionText;
            ExactVersionField.HasInputValue = IsExactVersionPolicy;
        }

        SelectedMembersField?.ReplaceStringArrayValues(
            _selectedMemberNames,
            hasInputValue: _selectedMemberNames.Count > 0);
        errorMessage = string.Empty;
        return true;
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(ShareSearchTextLabel));
        OnPropertyChanged(nameof(ShareNameText));
        OnPropertyChanged(nameof(VersionPolicyText));
        OnPropertyChanged(nameof(LatestText));
        OnPropertyChanged(nameof(ExactVersionTextLabel));
        OnPropertyChanged(nameof(MembersText));
        OnPropertyChanged(nameof(SearchText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(LoadMoreText));
        OnPropertyChanged(nameof(ClearMembersText));
    }

    public void AcceptChanges()
    {
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        CancelAndDispose(ref _shareRequestCts);
        CancelAndDispose(ref _versionRequestCts);
        CancelAndDispose(ref _memberRequestCts);
    }

    private async Task LoadSharesAsync(bool reset)
    {
        var requestVersion = ++_shareRequestVersion;
        var cancellationToken = BeginRequest(ref _shareRequestCts);
        IsLoadingShares = true;
        ErrorMessage = null;
        if (reset)
        {
            _shareOffset = 0;
            HasMoreShares = false;
        }

        try
        {
            var response = await _catalogService.SearchSharesAsync(
                NormalizeQuery(ShareSearchText),
                _shareOffset,
                SharePageSize,
                cancellationToken);
            if (requestVersion != _shareRequestVersion || _disposed)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = DescribeError(response.Error);
                return;
            }

            if (reset)
            {
                ShareOptions.Clear();
            }

            foreach (var entry in response.Data.Items)
            {
                if (ShareOptions.All(option => option.ShareName != entry.ShareName))
                {
                    ShareOptions.Add(new SharedPublicationShareOptionViewModel(entry));
                }
            }

            _shareOffset = response.Data.Offset + response.Data.Items.Length;
            HasMoreShares = response.Data.HasMore;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (!_disposed && requestVersion == _shareRequestVersion)
            {
                ErrorMessage = ex.Message;
            }
        }
        finally
        {
            if (requestVersion == _shareRequestVersion)
            {
                IsLoadingShares = false;
            }
        }
    }

    private async Task LoadVersionsAsync(bool reset)
    {
        var normalizedShareName = ShareName?.Trim() ?? string.Empty;
        if (normalizedShareName.Length == 0)
        {
            ErrorMessage = _localizationService.GetString(
                "node_config.shared.error.share_name_required");
            return;
        }

        if (reset && !string.Equals(
            _directoryShareName,
            normalizedShareName,
            StringComparison.Ordinal))
        {
            _selectedMemberNames.Clear();
            _selectedPublicationId = null;
        }

        _directoryShareName = normalizedShareName;
        var requestVersion = ++_versionRequestVersion;
        var cancellationToken = BeginRequest(ref _versionRequestCts);
        IsLoadingVersions = true;
        ErrorMessage = null;
        if (reset)
        {
            _versionOffset = 0;
            _versionsFullyLoaded = false;
            _versionDirectoryLoaded = false;
            HasMoreVersions = false;
            VersionOptions.Clear();
            SelectedVersionOption = null;
            ResetMembers();
        }

        try
        {
            var response = await _catalogService.ListVersionsAsync(
                normalizedShareName,
                _versionOffset,
                VersionPageSize,
                cancellationToken);
            if (requestVersion != _versionRequestVersion || _disposed)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = DescribeError(response.Error);
                return;
            }

            foreach (var summary in response.Data.Items)
            {
                if (VersionOptions.All(
                    option => option.PublicationId != summary.PublicationId))
                {
                    VersionOptions.Add(
                        new SharedPublicationVersionOptionViewModel(summary));
                }
            }

            _versionOffset = response.Data.Offset + response.Data.Items.Length;
            HasMoreVersions = response.Data.HasMore;
            _versionDirectoryLoaded = true;
            _versionsFullyLoaded = !response.Data.HasMore;
            if (reset)
            {
                SelectConfiguredVersion();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (!_disposed && requestVersion == _versionRequestVersion)
            {
                ErrorMessage = ex.Message;
            }
        }
        finally
        {
            if (requestVersion == _versionRequestVersion)
            {
                IsLoadingVersions = false;
            }
        }
    }

    private async Task LoadMembersAsync(bool reset)
    {
        var version = SelectedVersionOption;
        if (version is null)
        {
            return;
        }

        var requestVersion = ++_memberRequestVersion;
        var cancellationToken = BeginRequest(ref _memberRequestCts);
        IsLoadingMembers = true;
        ErrorMessage = null;
        if (reset)
        {
            _memberOffset = 0;
            _membersFullyLoaded = false;
            _memberDirectoryLoaded = false;
            MemberOptions.Clear();
        }

        try
        {
            var response = await _catalogService.ListMembersAsync(
                version.PublicationId,
                _memberOffset,
                MemberPageSize,
                cancellationToken);
            if (requestVersion != _memberRequestVersion
                || _disposed
                || SelectedVersionOption?.PublicationId != version.PublicationId)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                ErrorMessage = DescribeError(response.Error);
                return;
            }

            foreach (var member in response.Data.Items)
            {
                if (MemberOptions.All(option => option.ExportName != member.ExportName))
                {
                    MemberOptions.Add(
                        new SharedPublicationMemberOptionViewModel(
                            member,
                            _selectedMemberNames.Contains(
                                member.ExportName,
                                StringComparer.Ordinal),
                            HandleMemberSelectionChanged));
                }
            }

            _memberOffset = response.Data.Offset + response.Data.Items.Length;
            HasMoreMembers = response.Data.HasMore;
            _memberDirectoryLoaded = true;
            _membersFullyLoaded = !response.Data.HasMore;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            if (!_disposed && requestVersion == _memberRequestVersion)
            {
                ErrorMessage = ex.Message;
            }
        }
        finally
        {
            if (requestVersion == _memberRequestVersion)
            {
                IsLoadingMembers = false;
            }
        }
    }

    private void SelectConfiguredVersion()
    {
        SharedPublicationVersionOptionViewModel? option;
        if (IsExactVersionPolicy
            && int.TryParse(
                ExactVersionText,
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out var exactVersion))
        {
            option = VersionOptions.FirstOrDefault(
                item => item.PublicationVersion == exactVersion);
        }
        else
        {
            option = VersionOptions.FirstOrDefault(item => item.IsLatestPublished);
        }

        SelectedVersionOption = option;
    }

    private void SetVersionPolicy(bool exact)
    {
        IsExactVersionPolicy = exact;
        IsLatestVersionPolicy = !exact;
        VersionPolicyField.InputValue = exact ? "EXACT_VERSION" : "LATEST";
        VersionPolicyField.HasInputValue = true;
        if (!exact && ExactVersionField is not null)
        {
            ExactVersionField.HasInputValue = false;
        }

        SelectConfiguredVersion();
    }

    private void HandleMemberSelectionChanged(
        SharedPublicationMemberOptionViewModel member)
    {
        var changed = false;
        var index = _selectedMemberNames.FindIndex(
            name => string.Equals(name, member.ExportName, StringComparison.Ordinal));
        if (member.IsSelected && index < 0)
        {
            _selectedMemberNames.Add(member.ExportName);
            changed = true;
        }
        else if (!member.IsSelected && index >= 0)
        {
            _selectedMemberNames.RemoveAt(index);
            changed = true;
        }

        if (changed && !_suppressConfigChanged)
        {
            ConfigChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    private void ResetMembers()
    {
        ++_memberRequestVersion;
        CancelAndDispose(ref _memberRequestCts);
        _memberOffset = 0;
        _membersFullyLoaded = false;
        _memberDirectoryLoaded = false;
        HasMoreMembers = false;
        MemberOptions.Clear();
    }

    private CancellationToken BeginRequest(ref CancellationTokenSource? source)
    {
        CancelAndDispose(ref source);
        source = CancellationTokenSource.CreateLinkedTokenSource(_lifetimeToken);
        return source.Token;
    }

    private static void CancelAndDispose(ref CancellationTokenSource? source)
    {
        if (source is null)
        {
            return;
        }

        source.Cancel();
        source.Dispose();
        source = null;
    }

    private string DescribeError(ApiErrorDto? error)
    {
        return error?.Message
            ?? _localizationService.GetString("node_config.shared.error.request_failed");
    }

    private static string? NormalizeQuery(string? value)
    {
        var normalized = value?.Trim() ?? string.Empty;
        return normalized.Length == 0 ? null : normalized;
    }

    private static NodeConfigEditableFieldInputViewModel? FindField(
        IReadOnlyList<NodeConfigEditableFieldInputViewModel> fields,
        string name)
    {
        return fields.FirstOrDefault(
            field => string.Equals(field.Name, name, StringComparison.Ordinal));
    }

    partial void OnShareNameChanged(string value)
    {
        ShareNameField.InputValue = value;
        ShareNameField.HasInputValue = !string.IsNullOrWhiteSpace(value);
    }

    partial void OnExactVersionTextChanged(string value)
    {
        if (IsExactVersionPolicy && ExactVersionField is not null)
        {
            ExactVersionField.InputValue = value;
            ExactVersionField.HasInputValue = !string.IsNullOrWhiteSpace(value);
        }
    }

    partial void OnSelectedShareOptionChanged(
        SharedPublicationShareOptionViewModel? value)
    {
        if (value is null)
        {
            return;
        }

        ShareName = value.ShareName;
        _ = LoadVersionsAsync(reset: true);
    }

    partial void OnSelectedVersionOptionChanged(
        SharedPublicationVersionOptionViewModel? value)
    {
        if (value is null)
        {
            ResetMembers();
            return;
        }

        if (_selectedPublicationId is not null
            && !string.Equals(
                _selectedPublicationId,
                value.PublicationId,
                StringComparison.Ordinal))
        {
            var selectedMembersChanged = _selectedMemberNames.Count > 0;
            _selectedMemberNames.Clear();
            if (selectedMembersChanged)
            {
                ConfigChanged?.Invoke(this, EventArgs.Empty);
            }
        }

        _selectedPublicationId = value.PublicationId;
        if (IsExactVersionPolicy)
        {
            ExactVersionText = value.PublicationVersion.ToString(
                CultureInfo.InvariantCulture);
        }

        _ = LoadMembersAsync(reset: true);
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    partial void OnHasMoreSharesChanged(bool value)
    {
        LoadMoreSharesCommand.NotifyCanExecuteChanged();
    }

    partial void OnHasMoreVersionsChanged(bool value)
    {
        LoadMoreVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnHasMoreMembersChanged(bool value)
    {
        LoadMoreMembersCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingSharesChanged(bool value)
    {
        LoadMoreSharesCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingVersionsChanged(bool value)
    {
        LoadMoreVersionsCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingMembersChanged(bool value)
    {
        LoadMoreMembersCommand.NotifyCanExecuteChanged();
    }
}
