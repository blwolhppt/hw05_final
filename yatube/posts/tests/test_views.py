from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post, Comment, Follow
from ..views import AMOUNT_OF_POSTS

User = get_user_model()


class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.follower = User.objects.create_user(username='follower')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='description',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post_0 = Post.objects.create(
            id=0,
            author=cls.user,
            text='Тестовый пост 0',
            group=cls.group,
            image=cls.uploaded,
        )

        cls.post_1 = Post.objects.create(
            id=1,
            author=cls.user,
            text='Тестовый пост 1',
            group=None,
        )

        cls.comment_0 = Comment.objects.create(
            post=cls.post_0,
            author=cls.user,
            text='Комментарий под постом post_0'

        )
        cls.follow = Follow.objects.create(
            user=cls.follower,
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = self.__class__.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertTemplateUsed(response, 'posts/index.html')
        self.assertIn('page_obj', response.context)
        posts = response.context.get('page_obj').object_list
        expected = list(Post.objects.all())
        self.assertEqual(list(posts), expected)

    def test_cache(self):
        """ Тест кэша."""
        response_new = self.guest_client.get(reverse('posts:index')).content
        self.post_1.delete()
        response_delete = self.guest_client.get(reverse('posts:index')).content
        self.assertEqual(response_new, response_delete)
        cache.clear()
        response_cache = self.guest_client.get(reverse('posts:index')).content
        self.assertNotEqual(response_new, response_cache)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertTemplateUsed(response, 'posts/group_list.html')
        self.assertIn('group', response.context)
        self.assertIn('page_obj', response.context)
        posts = response.context.get('page_obj').object_list
        group = response.context.get('group')
        expected = list(Post.objects.filter(group_id=self.group.id))

        self.assertEqual(posts, expected)
        self.assertEqual(group, self.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertTemplateUsed(response, 'posts/profile.html')
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        posts = response.context.get('page_obj').object_list
        author = response.context.get('author')
        expected = list(Post.objects.filter(author_id=self.user.id))

        self.assertEqual(posts, expected)
        self.assertEqual(author, self.user)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом(+ком)."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post_0.id}))

        self.assertTemplateUsed(response, 'posts/post_detail.html')
        self.assertIn('user_post', response.context)
        self.assertIn('all_comments', response.context)
        post = response.context.get('user_post')
        comment = response.context['all_comments'][0]
        self.assertEqual(post, self.post_0)
        self.assertEqual(comment, self.comment_0)

    def test_create_post_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertTemplateUsed(response, 'posts/create_post.html')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self):
        """Шаблон edit_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post_0.id}))
        self.assertTemplateUsed(response, 'posts/create_post.html')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_404(self):
        """Проверка ошибки 404."""
        response = self.guest_client.get('/nonexist-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_following(self):
        """Проверка возможности подписок"""
        self.authorized_follower.get(
            reverse('posts:profile_follow', args=(self.user,)))

        self.assertTrue(Follow.objects.filter(user=self.follower,
                                              author=self.user).exists())

    def test_unfollowing(self):
        """Проверка возможности отписок"""
        self.authorized_follower.get(
            reverse('posts:profile_unfollow', args=(self.user,)))

        self.assertFalse(Follow.objects.filter(user=self.follower,
                                               author=self.user).exists())


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        """Создаем автора и группу."""
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='description',
        )
        for i in range(0, 11):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_page(self):
        """Проверка пагинации index."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), AMOUNT_OF_POSTS)

        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_group_list_page(self):
        """Проверка пагинации group_post."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response.context['page_obj']), AMOUNT_OF_POSTS)

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
            + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_profile_page(self):
        """Проверка пагинации profile."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(len(response.context['page_obj']), AMOUNT_OF_POSTS)

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
            + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 1)
