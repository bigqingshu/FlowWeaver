using System;
using System.Collections.ObjectModel;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationListItemViewModel
{
    public SharedPublicationListItemViewModel(SharedPublicationDto publication)
    {
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

    public string VersionText => $"v{PublicationVersion}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string MemberCountText => $"{Members.Count} member(s)";

    public string InputSnapshotText =>
        string.IsNullOrWhiteSpace(InputSnapshotId) ? "-" : InputSnapshotId;
}
