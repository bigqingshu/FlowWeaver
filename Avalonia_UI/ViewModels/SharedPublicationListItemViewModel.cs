using System;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationListItemViewModel
{
    private readonly int memberCount;

    public SharedPublicationListItemViewModel(
        SharedPublicationDto publication,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        PublicationId = publication.PublicationId;
        ShareName = publication.ShareName;
        PublicationVersion = publication.PublicationVersion;
        ProducerWorkflowId = publication.ProducerWorkflowId;
        ProducerRunId = publication.ProducerRunId;
        Status = publication.Status;
        InputSnapshotId = publication.InputSnapshotId;
        CreatedAt = publication.CreatedAt;
        Members = new ObservableCollection<SharedPublicationMemberListItemViewModel>(
            publication.Members.Select(member => new SharedPublicationMemberListItemViewModel(member)));
        memberCount = publication.Members.Length;
    }

    public SharedPublicationListItemViewModel(
        SharedPublicationSummaryDto publication,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        PublicationId = publication.PublicationId;
        ShareName = publication.ShareName;
        PublicationVersion = publication.PublicationVersion;
        ProducerWorkflowId = publication.ProducerWorkflowId;
        ProducerRunId = publication.ProducerRunId;
        Status = publication.Status;
        InputSnapshotId = publication.InputSnapshotId;
        CreatedAt = publication.CreatedAt;
        Members = new ObservableCollection<SharedPublicationMemberListItemViewModel>();
        memberCount = publication.MemberCount;
    }

    public string PublicationId { get; }

    public string ShareName { get; }

    public int PublicationVersion { get; }

    public string ProducerWorkflowId { get; }

    public string ProducerRunId { get; }

    public string Status { get; }

    public string? InputSnapshotId { get; }

    public DateTimeOffset CreatedAt { get; }

    public ObservableCollection<SharedPublicationMemberListItemViewModel> Members { get; }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string VersionText => $"v{PublicationVersion}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string MemberCountText => DisplayTextFormatter.FormatMemberCount(memberCount);

    public string InputSnapshotText =>
        string.IsNullOrWhiteSpace(InputSnapshotId) ? "-" : InputSnapshotId;
}
